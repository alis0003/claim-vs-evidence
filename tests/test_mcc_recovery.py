import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import reconcile_mcc as r
from publisher import Stop, UTC
from github_journal import GitHubJournal, REPOSITORY
from git_journal import REF
from test_hosted import LocalREST
from test_git_journal import git

NOW=dt.datetime(2026,10,31,14,tzinfo=UTC)
class API:
    def __init__(self,status='PUBLISHED'):self.status=status;self.calls=[]
    def call(self,method,path,**params):
        self.calls.append((method,path,params))
        if path=='me':return {'username':'claimvsevidence','user_id':'123'}
        return {'status_code':self.status}

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)
        git(self.repo,'init','--bare');git(self.repo,'config','user.name','Test');git(self.repo,'config','user.email','test@invalid')
        self.other=['b'*64,'sent','2026-10-30T06:00:00+00:00','123','456']
        self.initial={'version':1,'owner':None,'jobs':{r.CLAIM:r.ORIGINAL_ROW.copy(),'a'*64:self.other.copy()}}
        blob=git(self.repo,'hash-object','-w','--stdin',input=json.dumps(self.initial)+'\n')
        tree=git(self.repo,'mktree',input=f'100644 blob {blob}\tstate.json\n')
        self.head=git(self.repo,'commit-tree',tree,input='Test snapshot')
        git(self.repo,'update-ref',REF,self.head)
        self.backend=LocalREST(self.repo);self.api=API()
        self.config=dict(repository=REPOSITORY,username='claimvsevidence',active=True,parent_confirmed_secret_ready=True,initial_queue_reviewed=True,activation_at='2026-10-28T06:07:35.862082+00:00',end_at='2026-11-27T06:07:35.862082+00:00',state_genesis=self.head)
        self.env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=REPOSITORY,GITHUB_REF='refs/heads/main',GITHUB_SHA='b'*40,GITHUB_EVENT_NAME='workflow_dispatch',PUBLISHING_ENABLED='true',INSTAGRAM_ACCESS_TOKEN='fake',GITHUB_TOKEN='fake')
        self.pin=patch.object(r,'HEAD',self.head);self.pin.start()
    def tearDown(self):self.pin.stop();self.tmp.cleanup()
    def run_recovery(self):return r.run(self.config,self.env,lambda:NOW,lambda _:self.backend,lambda _:self.api)
    def state(self):return GitHubJournal(self.backend,self.head).state
    def test_published_only_target_and_no_post(self):
        result=self.run_recovery();state=self.state()
        self.assertEqual(result['outcome'],'reconciled_sent');self.assertEqual(result['unresolved_jobs'],0)
        self.assertEqual(state['jobs']['a'*64],self.other);self.assertIsNone(state['owner'])
        self.assertEqual(state['jobs'][r.CLAIM],[r.FINGERPRINT,'sent',NOW.isoformat(),r.CONTAINER,None])
        self.assertEqual([c[:2] for c in self.api.calls],[('GET','me'),('GET',r.CONTAINER)])
    def test_repeat_fails_closed_before_instagram(self):
        self.run_recovery();self.api.calls=[]
        with self.assertRaisesRegex(Stop,'recovery_snapshot_changed'):self.run_recovery()
        self.assertEqual(self.api.calls,[])
    def test_nonpublished_stays_held(self):
        for status in ['FINISHED','IN_PROGRESS','ERROR','EXPIRED',None]:
            with self.subTest(status=status):
                self.api.status=status
                # Restore local test-only branch between cases.
                git(self.repo,'update-ref',REF,self.head)
                with self.assertRaisesRegex(Stop,'recovery_still_quarantined'):self.run_recovery()
                self.assertEqual(self.state()['jobs'],self.initial['jobs'])
                self.assertIsNone(self.state()['owner'])
    def test_wrong_identity(self):
        self.api.call=lambda *a,**kw:{'username':'other','user_id':'123'}
        with self.assertRaisesRegex(Stop,'wrong_identity'):self.run_recovery()
        self.assertEqual(self.state()['jobs'],self.initial['jobs'])
    def test_instagram_post_and_other_get_denied(self):
        api=r.ReadOnlyInstagram(self.api)
        for method,path in [('POST','123/media_publish'),('GET','123'),('DELETE',r.CONTAINER)]:
            with self.assertRaisesRegex(Stop,'recovery_read_only'):api.call(method,path)
        self.assertEqual(self.api.calls,[])
    def test_untrusted_event(self):
        self.env['GITHUB_EVENT_NAME']='schedule'
        with self.assertRaises(Stop):self.run_recovery()
        self.assertEqual(self.backend.calls,[])
    def test_lost_ack_never_queries_instagram(self):
        self.backend.lose_ack=True
        with self.assertRaisesRegex(Stop,'durable_checkpoint_uncertain'):self.run_recovery()
        self.assertEqual(self.api.calls,[])
    def test_scope_guard(self):
        journal=r.MCCJournal(self.backend,self.head)
        for mutation in ['other','media','phase','container']:
            updated=copy.deepcopy(journal.state)
            if mutation=='other':updated['jobs']['a'*64][1]='publishing'
            elif mutation=='media':updated['jobs'][r.CLAIM][4]='123'
            elif mutation=='phase':updated['jobs'][r.CLAIM][1]='created'
            else:updated['jobs'][r.CLAIM][3]='987'
            with self.assertRaises(Stop):journal._checkpoint(updated)
