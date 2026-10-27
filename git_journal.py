"""Repository-backed journal, exercised only against local bare repositories.
No CLI and no deployment wiring. Remote must already contain a pinned genesis.
"""
import contextlib
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from publisher import Stop, require, timestamp

REF='refs/heads/publishing-state'
HEX=re.compile(r'^[0-9a-f]{40}$')


class GitJournal:
    """Each checkpoint is an acknowledged normal fast-forward push.

    A single remote owner fences ALL claims. A crashed owner's lock has no TTL:
    recovery must be explicit. Never rebase, merge, force push or replay a failed
    push. The caller must protect the state branch from deletion/rewind/tampering.
    Current transport deliberately accepts LOCAL bare repositories only. Enabling
    an authorized hosted transport is a separate reviewed deployment change.
    """
    def __init__(self, remote, genesis):
        remote=Path(remote)
        require(remote.is_absolute() and remote.is_dir() and (remote/'HEAD').is_file()
                and (remote/'objects').is_dir(), 'local_bare_remote_required')
        require(bool(HEX.fullmatch(genesis)), 'invalid_genesis')
        self.remote=str(remote.resolve())
        self.genesis=genesis
        self.tmp=tempfile.TemporaryDirectory(prefix='claim-state-')
        self.work=Path(self.tmp.name)
        self.owner=None
        self.head=None
        self.state=None
        self.poisoned=False
        try:
            self._git('init','--bare',str(self.work))
            self._load()
        except BaseException:
            self.tmp.cleanup()
            raise

    def close(self):
        self.tmp.cleanup()

    def _git(self,*args,input=None):
        # No inherited Git config, hooks, credentials, remote output or shell.
        env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT='0',GIT_ALLOW_PROTOCOL='file',
                   GIT_AUTHOR_NAME='Public state journal',GIT_AUTHOR_EMAIL='state@invalid',
                   GIT_COMMITTER_NAME='Public state journal',GIT_COMMITTER_EMAIL='state@invalid')
        try:
            r=subprocess.run(['git','-c','core.hooksPath=/dev/null','-C',str(self.work),*args],
                             input=input,text=True,capture_output=True,env=env,timeout=20)
            require(r.returncode==0, 'git_operation_failed')
            return r.stdout.strip()
        except Stop:
            raise
        except Exception:
            raise Stop('git_transport_uncertain') from None

    def _fetch(self):
        self._git('fetch','--no-tags',self.remote,REF)
        head=self._git('rev-parse','FETCH_HEAD')
        require(bool(HEX.fullmatch(head)), 'invalid_remote_head')
        self._git('merge-base','--is-ancestor',self.genesis,head)
        return head

    def _decode(self,head):
        return self.decode_raw(self._git('show',head+':state.json'))

    @staticmethod
    def decode_raw(raw):
        try:
            require(len(raw)<=5_000_000,'invalid_remote_state')
            s=json.loads(raw)
            require(set(s)=={'version','owner','jobs'} and s['version']==1 and isinstance(s['jobs'],dict), 'invalid_remote_state')
            require(s['owner'] is None or bool(re.fullmatch('[a-f0-9]{32}',s['owner'])), 'invalid_remote_state')
            for cid,r in s['jobs'].items():
                require(bool(re.fullmatch('[a-f0-9]{64}',cid)) and isinstance(r,list) and len(r)==5, 'invalid_remote_state')
                fp,phase,at,container,media=r
                require(bool(re.fullmatch('[a-f0-9]{64}',fp)) and phase in {'creating','created','publishing','sent'}, 'invalid_remote_state')
                timestamp(at)
                require(container is None or bool(re.fullmatch('[0-9]+',container)), 'invalid_remote_state')
                require(media is None or bool(re.fullmatch('[0-9]+',media)), 'invalid_remote_state')
                require(phase=='creating' or container is not None, 'invalid_remote_state')
            return s
        except Stop:
            raise
        except Exception:
            raise Stop('invalid_remote_state') from None

    def _load(self):
        self.head=self._fetch()
        self.state=self._decode(self.head)

    def _checkpoint(self, updated):
        require(not self.poisoned,'journal_poisoned')
        try:
            # Explicit optimistic head check plus normal push's atomic FF check.
            require(self._fetch()==self.head,'remote_head_changed')
            raw=json.dumps(updated,sort_keys=True,separators=(',',':'))+'\n'
            blob=self._git('hash-object','-w','--stdin',input=raw)
            tree=self._git('mktree',input=f'100644 blob {blob}\tstate.json\n')
            commit=self._git('commit-tree',tree,'-p',self.head,input='Checkpoint public publishing state\n')
            self._git('push','--porcelain',self.remote,commit+':'+REF)
            require(self._fetch()==commit,'checkpoint_unconfirmed')
            require(self._decode(commit)==updated,'checkpoint_unconfirmed')
            self.head,self.state=commit,copy.deepcopy(updated)
        except Exception:
            # An accepted push with a lost ACK is uncertain: never assume failure
            # means absence, never retry the push, and never proceed to API POST.
            self.poisoned=True
            raise Stop('durable_checkpoint_uncertain') from None

    @contextlib.contextmanager
    def exclusive(self):
        require(self.owner is None and not self.poisoned,'journal_unavailable')
        self._load()
        require(self.state['owner'] is None,'remote_owner_requires_review')
        owner=uuid.uuid4().hex
        updated=copy.deepcopy(self.state);updated['owner']=owner
        self._checkpoint(updated)
        self.owner=owner
        try:
            yield
        finally:
            if not self.poisoned:
                # Releasing a lease cannot clear any job or uncertainty.
                updated=copy.deepcopy(self.state);updated['owner']=None
                self._checkpoint(updated)
            self.owner=None

    def row(self,cid):
        r=self.state['jobs'].get(cid)
        return tuple(r) if r else None

    def times(self,exclude=None):
        return [r[2] for cid,r in self.state['jobs'].items() if cid!=exclude]

    def unresolved(self,exclude=None):
        return any(r[1]!='sent' for cid,r in self.state['jobs'].items() if cid!=exclude)

    def save(self,cid,fingerprint,phase,now,container=None,media=None):
        require(self.owner is not None and self.state['owner']==self.owner,'remote_owner_required')
        require(bool(re.fullmatch('[a-f0-9]{64}',cid)) and bool(re.fullmatch('[a-f0-9]{64}',fingerprint)), 'invalid_state_record')
        old=self.row(cid)
        allowed={None:{'creating'},'creating':{'created'},'created':{'publishing','sent'},'publishing':{'sent'},'sent':set()}
        require(phase in allowed[old[1] if old else None], 'invalid_state_transition')
        if old:
            require(old[0]==fingerprint and (old[3] is None or old[3]==container), 'changed_state_record')
        updated=copy.deepcopy(self.state)
        updated['jobs'][cid]=[fingerprint,phase,now.isoformat(),container,media]
        self._checkpoint(updated)

    def inspect(self):
        """Read-only fresh snapshot, including public owner and exact head."""
        head=self._fetch()
        return head,self._decode(head)

    def recover_abandoned_owner(self, expected_head, expected_owner, *, stopped_confirmed=False):
        """Explicit operator action AFTER stopping original run; no API calls.
        Only removes the named lock at the inspected head; all job states remain.
        It is NOT reconciliation and does not authorize a POST replay.
        """
        require(stopped_confirmed is True,'stop_original_runner_first')
        require(self.owner is None and not self.poisoned,'journal_unavailable')
        self._load()
        require(self.head==expected_head and self.state['owner']==expected_owner
                and expected_owner is not None,'recovery_head_or_owner_changed')
        updated=copy.deepcopy(self.state);updated['owner']=None
        self._checkpoint(updated)
        return 'owner_released_jobs_still_require_reconciliation'
