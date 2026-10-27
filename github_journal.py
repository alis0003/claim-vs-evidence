"""Authorized-repository-only GitHub REST transport; no token files or retries."""
import base64
import copy
import http.client
import json
import re
import ssl
from git_journal import GitJournal, HEX
from publisher import Stop, require

REPOSITORY='alis0003/claim-vs-evidence'
PREFIX='/repos/'+REPOSITORY+'/'

class GitHubAPI:
    def __init__(self, token):
        require(isinstance(token,str) and token.strip() and '\r' not in token and '\n' not in token,'missing_github_token')
        self._token=token

    def call(self,method,path,body=None):
        require(method in {'GET','POST','PATCH'} and path.startswith(PREFIX)
                and '..' not in path.replace('...','') and '?' not in path and '#' not in path, 'unsafe_github_path')
        connection=None
        try:
            connection=http.client.HTTPSConnection('api.github.com',timeout=20,context=ssl.create_default_context())
            headers={'Authorization':'Bearer '+self._token,'Accept':'application/vnd.github+json',
                     'X-GitHub-Api-Version':'2026-03-10','User-Agent':'claim-vs-evidence-journal',
                     'Content-Type':'application/json'}
            connection.request(method,path,json.dumps(body).encode() if body is not None else None,headers)
            response=connection.getresponse()
            require(response.status in {200,201},'github_request_failed')
            raw=response.read(8_000_001)
            require(len(raw)<=8_000_000,'github_response_too_large')
            result=json.loads(raw)
            require(isinstance(result,dict),'invalid_github_response')
            return result
        except Stop:raise
        except Exception:raise Stop('github_transport_uncertain') from None
        finally:
            if connection:connection.close()


def sha(value):
    require(isinstance(value,str) and bool(HEX.fullmatch(value)),'invalid_github_sha')
    return value


class GitHubJournal(GitJournal):
    """Same fencing/recovery protocol, REST Git objects + non-force ref updates.
    No remote branch creation, credential discovery, git subprocess or local state.
    """
    def __init__(self,api,genesis):
        self.api=api;self.genesis=sha(genesis)
        self.owner=None;self.head=None;self.state=None;self.poisoned=False
        self._load()

    def close(self):pass

    def _fetch(self):
        result=self.api.call('GET',PREFIX+'git/ref/heads/publishing-state')
        require(result.get('ref')=='refs/heads/publishing-state' and result.get('object',{}).get('type')=='commit','invalid_remote_head')
        head=sha(result['object']['sha'])
        comparison=self.api.call('GET',PREFIX+'compare/'+self.genesis+'...'+head)
        require(comparison.get('status') in {'identical','ahead'},'untrusted_state_history')
        return head

    def _decode(self,head):
        commit=self.api.call('GET',PREFIX+'git/commits/'+sha(head))
        tree=self.api.call('GET',PREFIX+'git/trees/'+sha(commit['tree']['sha']))
        require(tree.get('truncated') is False,'invalid_remote_state')
        entries=tree.get('tree')
        require(isinstance(entries,list) and len(entries)==1 and entries[0].get('path')=='state.json'
                and entries[0].get('type')=='blob' and entries[0].get('mode')=='100644','invalid_remote_state')
        blob=self.api.call('GET',PREFIX+'git/blobs/'+sha(entries[0]['sha']))
        require(blob.get('encoding')=='base64','invalid_remote_state')
        try:
            raw=base64.b64decode(''.join(blob['content'].split()),validate=True).decode('utf-8')
        except Exception:raise Stop('invalid_remote_state') from None
        return self.decode_raw(raw)

    def _checkpoint(self,updated):
        require(not self.poisoned,'journal_poisoned')
        try:
            require(self._fetch()==self.head,'remote_head_changed')
            raw=json.dumps(updated,sort_keys=True,separators=(',',':'))+'\n'
            self.decode_raw(raw)
            blob=sha(self.api.call('POST',PREFIX+'git/blobs',{'content':raw,'encoding':'utf-8'})['sha'])
            tree=sha(self.api.call('POST',PREFIX+'git/trees',{'tree':[{'path':'state.json','mode':'100644','type':'blob','sha':blob}]})['sha'])
            commit=sha(self.api.call('POST',PREFIX+'git/commits',{'message':'Checkpoint public publishing state','tree':tree,'parents':[self.head]})['sha'])
            # No force and no implicit merge/rebase. Sibling commits cannot both win.
            require(self._fetch()==self.head,'remote_head_changed')
            result=self.api.call('PATCH',PREFIX+'git/refs/heads/publishing-state',{'sha':commit,'force':False})
            require(result.get('object',{}).get('sha')==commit,'checkpoint_unconfirmed')
            require(self._fetch()==commit and self._decode(commit)==updated,'checkpoint_unconfirmed')
            self.head,self.state=commit,copy.deepcopy(updated)
        except Exception:
            self.poisoned=True
            raise Stop('durable_checkpoint_uncertain') from None
