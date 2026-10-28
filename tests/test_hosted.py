import base64
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import http.client
import hashlib

from git_journal import REF
from github_journal import GitHubAPI, GitHubJournal, PREFIX, REPOSITORY
from test_git_journal import git
from test_publisher import API, NOW, job, fetch
import publisher as p
import pilot

class LocalREST:
    """GitHub Git REST semantics simulated with LOCAL git objects, no HTTP."""
    def __init__(self,repo):self.repo=repo;self.fail_patch=False;self.lose_ack=False;self.calls=[]
    def call(self,method,path,body=None):
        self.calls.append((method,path,body));self.assert_path(path)
        part=path[len(PREFIX):]
        if method=='GET':
            if part=='git/ref/heads/publishing-state':return {'ref':REF,'object':{'type':'commit','sha':git(self.repo,'rev-parse',REF)}}
            if part.startswith('compare/'):
                start,end=part[8:].split('...')
                try:git(self.repo,'merge-base','--is-ancestor',start,end)
                except Exception:return {'status':'diverged'}
                return {'status':'identical' if start==end else 'ahead'}
            if part.startswith('git/commits/'):
                return {'tree':{'sha':git(self.repo,'show','-s','--format=%T',part.split('/')[-1])}}
            if part.startswith('git/trees/'):
                entries=[]
                for line in git(self.repo,'ls-tree',part.split('/')[-1]).splitlines():
                    meta,path=line.split('\t');mode,kind,sha=meta.split()
                    entries.append({'path':path,'mode':mode,'type':kind,'sha':sha})
                return {'tree':entries,'truncated':False}
            if part.startswith('git/blobs/'):
                raw=git(self.repo,'cat-file','blob',part.split('/')[-1])+'\n'
                return {'encoding':'base64','content':base64.b64encode(raw.encode()).decode()}
        if method=='POST':
            if part=='git/blobs':return {'sha':git(self.repo,'hash-object','-w','--stdin',input=body['content'])}
            if part=='git/trees':
                rows=''.join(f"{r['mode']} {r['type']} {r['sha']}\t{r['path']}\n" for r in body['tree'])
                return {'sha':git(self.repo,'mktree',input=rows)}
            if part=='git/commits':return {'sha':git(self.repo,'commit-tree',body['tree'],'-p',body['parents'][0],input=body['message'])}
        if method=='PATCH':
            assert part=='git/refs/heads/publishing-state' and body['force'] is False
            if self.fail_patch:raise p.Stop('simulated_rejection')
            current=git(self.repo,'rev-parse',REF)
            git(self.repo,'merge-base','--is-ancestor',current,body['sha'])
            git(self.repo,'update-ref',REF,body['sha'],current)
            if self.lose_ack:raise p.Stop('simulated_lost_ack')
            return {'object':{'sha':body['sha']}}
        raise AssertionError((method,path))
    def assert_path(self,path):assert path.startswith(PREFIX)

class HostedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)
        git(self.repo,'init','--bare');git(self.repo,'config','user.name','Test');git(self.repo,'config','user.email','test@invalid')
        raw=json.dumps({'version':1,'owner':None,'jobs':{}})+'\n'
        blob=git(self.repo,'hash-object','-w','--stdin',input=raw)
        tree=git(self.repo,'mktree',input=f'100644 blob {blob}\tstate.json\n')
        self.genesis=git(self.repo,'commit-tree',tree,input='Genesis')
        git(self.repo,'update-ref',REF,self.genesis)
        self.backend=LocalREST(self.repo);self.j=GitHubJournal(self.backend,self.genesis);self.api=API()
        self.pub=p.Publisher(self.j,self.api,fetch,lambda:NOW)
    def tearDown(self):self.tmp.cleanup()
    def test_hosted_protocol_publishes_and_recovers_sent(self):
        self.assertEqual(self.pub.run(job(),True),'sent')
        fresh=GitHubJournal(self.backend,self.genesis)
        self.assertEqual(p.Publisher(fresh,self.api,fetch,lambda:NOW).run(job(),True),'already_sent')
        self.assertEqual(len(self.api.posts()),2)
        self.assertTrue(all(b['force'] is False for m,path,b in self.backend.calls if m=='PATCH'))
    def test_lost_ack_prevents_instagram_effect(self):
        self.backend.lose_ack=True
        with self.assertRaisesRegex(p.Stop,'durable_checkpoint_uncertain'):self.pub.run(job(),True)
        self.assertEqual(self.api.calls,[])
        fresh=GitHubJournal(self.backend,self.genesis)
        with self.assertRaisesRegex(p.Stop,'remote_owner_requires_review'):
            p.Publisher(fresh,self.api,fetch,lambda:NOW).run(job(),True)
    def test_remote_checkpoint_rejected_before_post(self):
        self.backend.fail_patch=True
        with self.assertRaisesRegex(p.Stop,'durable_checkpoint_uncertain'):self.pub.run(job(),True)
        self.assertEqual(self.api.posts(),[])
    def test_http_error_does_not_echo_token(self):
        with patch.object(http.client.HTTPSConnection,'request',side_effect=TimeoutError('Authorization super-secret')):
            with self.assertRaisesRegex(p.Stop,'^github_transport_uncertain$'):
                GitHubAPI('super-secret').call('GET',PREFIX+'git/ref/heads/publishing-state')
    def test_other_repository_denied(self):
        with self.assertRaisesRegex(p.Stop,'unsafe_github_path'):
            GitHubAPI('mock').call('GET','/repos/alis0003/SMMZZ/git/ref/heads/main')

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.config=dict(repository=REPOSITORY,username='claimvsevidence',active=True,
          parent_confirmed_secret_ready=True,initial_queue_reviewed=True,live_test_completed=False,
          activation_at=(NOW-dt.timedelta(days=1)).isoformat(),end_at=(NOW+dt.timedelta(days=29)).isoformat(),state_genesis='a'*40)
        self.env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=REPOSITORY,GITHUB_REF='refs/heads/main',
          GITHUB_SHA='b'*40,GITHUB_EVENT_NAME='workflow_dispatch',PUBLISHING_ENABLED='true')
    def test_exact_30_day_window(self):pilot.gate(self.config,self.env,NOW)
    def test_first_manual_live_test_does_not_require_completed_flag(self):
        self.assertFalse(self.config['live_test_completed'])
        self.env.update(INSTAGRAM_ACCESS_TOKEN='mock-instagram',GITHUB_TOKEN='mock-github')
        fake_publisher=unittest.mock.Mock()
        fake_publisher.run.return_value='sent'
        with patch.object(pilot,'GitHubJournal') as journal, patch.object(pilot,'Publisher',return_value=fake_publisher), patch.object(pilot,'published_receipt',return_value={'outcome':'sent'}), patch('builtins.print'):
            self.assertEqual(pilot.run(self.config,[job()],True,self.env,lambda:NOW,lambda t:object(),lambda t:object()),'sent')
        fake_publisher.run.assert_called_once()
        self.assertFalse(self.config['live_test_completed'])
    def test_media_receipt_requires_exact_id_and_instagram_permalink(self):
        journal=unittest.mock.Mock();journal.row.return_value=('fp','sent',NOW.isoformat(),'456','789')
        api=unittest.mock.Mock();api.call.return_value={'id':'789','permalink':'https://www.instagram.com/p/AbC123/'}
        self.assertEqual(pilot.published_receipt(api,journal,'claim')['media_id'],'789')
        api.call.assert_called_once_with('GET','789',fields='id,permalink')
        for response in [{'id':'000','permalink':'https://www.instagram.com/p/AbC123/'},{'id':'789','permalink':'https://evil.invalid/p/AbC123/'},{'id':'789','permalink':'https://www.instagram.com/p/AbC123/?token=mock'}]:
            api.call.return_value=response
            with self.assertRaises(p.Stop):pilot.published_receipt(api,journal,'claim')
    def test_end_is_exclusive(self):
        with self.assertRaisesRegex(p.Stop,'pilot_outside_window'):pilot.gate(self.config,self.env,NOW+dt.timedelta(days=29))
    def test_short_or_long_duration_rejected(self):
        for days in (28,30):
            c=copy.deepcopy(self.config);c['end_at']=(NOW+dt.timedelta(days=days)).isoformat()
            with self.assertRaises(p.Stop):pilot.gate(c,self.env,NOW)
    def test_disabled_even_with_secret(self):
        self.config['active']=False;self.env['INSTAGRAM_ACCESS_TOKEN']='mock'
        with self.assertRaisesRegex(p.Stop,'live_not_authorized'):pilot.run(self.config,[job()],True,self.env,lambda:NOW)
    def test_schedule_requires_successful_test(self):
        self.env['GITHUB_EVENT_NAME']='schedule'
        with self.assertRaisesRegex(p.Stop,'live_test_required'):pilot.gate(self.config,self.env,NOW)
    def test_schedule_requires_independent_producer_readiness(self):
        self.env['GITHUB_EVENT_NAME']='schedule';self.config['live_test_completed']=True
        with self.assertRaisesRegex(p.Stop,'producer_readiness_required'):pilot.gate(self.config,self.env,NOW)
        self.config['producer_fresh_run_verified']=True
        with self.assertRaisesRegex(p.Stop,'schedule_not_authorized'):pilot.gate(self.config,self.env,NOW)
        self.config['scheduled_publication_enabled']=True
        pilot.gate(self.config,self.env,NOW)
        with self.assertRaisesRegex(p.Stop,'pilot_outside_window'):
            pilot.gate(self.config,self.env,NOW+dt.timedelta(days=29))
    def test_pull_request_rejected(self):
        self.env['GITHUB_EVENT_NAME']='pull_request'
        with self.assertRaisesRegex(p.Stop,'untrusted_event'):pilot.gate(self.config,self.env,NOW)
    def test_dry_run_never_reads_secrets_or_api(self):
        def forbidden(*a):raise AssertionError('must be offline')
        self.assertEqual(pilot.run({},[job()],False,{},lambda:NOW,forbidden,forbidden),'dry_run_no_network')
    def test_expired_job_skipped_not_posted(self):
        j=job();j['run_before']=(NOW-dt.timedelta(minutes=1)).isoformat()
        self.assertEqual(pilot.run(self.config,[j],True,self.env,lambda:NOW),'no_due_jobs')
