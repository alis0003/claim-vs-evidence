import concurrent.futures
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import publisher as p
from git_journal import GitJournal, REF
from test_publisher import API, NOW, fetch, job


def git(path,*args,input=None):
    result=subprocess.run(['git','-C',str(path),*args],input=input,text=True,capture_output=True,check=True)
    return result.stdout.strip()

class DurableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.remote=self.root/'state.git';self.remote.mkdir();git(self.remote,'init','--bare')
        self.seed=self.root/'seed';self.seed.mkdir();git(self.seed,'init')
        git(self.seed,'config','user.name','Local test');git(self.seed,'config','user.email','test@invalid')
        (self.seed/'state.json').write_text(json.dumps(dict(version=1,owner=None,jobs={})))
        git(self.seed,'add','state.json');git(self.seed,'commit','-m','Public state genesis')
        self.genesis=git(self.seed,'rev-parse','HEAD');git(self.seed,'push',str(self.remote),'HEAD:'+REF)
        self.journals=[];self.api=API();self.job=job();self.j=self.new_journal();self.pub=self.publisher(self.j)
    def tearDown(self):
        for j in self.journals:j.close()
        self.tmp.cleanup()
    def new_journal(self):
        j=GitJournal(self.remote,self.genesis);self.journals.append(j);return j
    def publisher(self,j):return p.Publisher(j,self.api,fetch,lambda:NOW)
    def fails(self,code,fn):
        with self.assertRaisesRegex(p.Stop,'^'+code+'$'):fn()
    def remote_state(self):return json.loads(git(self.remote,'show',REF+':state.json'))
    def intercept_push(self,n,after=False):
        original=self.j._git;counter=[0]
        def wrapped(*args,**kwargs):
            if args[0]=='push':
                counter[0]+=1
                if counter[0]==n:
                    if after:original(*args,**kwargs)
                    raise p.Stop('simulated_lost_ack_or_rejection')
            return original(*args,**kwargs)
        return patch.object(self.j,'_git',side_effect=wrapped)
    def recover(self,j):
        head,state=j.inspect()
        return j.recover_abandoned_owner(head,state['owner'],stopped_confirmed=True)
    def test_success_remote_checkpoints_precede_posts(self):
        original=self.api.call
        def spy(method,path,**fields):
            if method=='POST':
                s=self.remote_state();r=s['jobs'][self.job['claim_id']]
                self.assertIsNotNone(s['owner'])
                self.assertEqual(r[1],'creating' if path.endswith('/media') else 'publishing')
                if path.endswith('media_publish'):self.assertEqual(r[3],'456')
            return original(method,path,**fields)
        self.api.call=spy
        self.assertEqual(self.pub.run(self.job,True),'sent')
        self.assertEqual(self.remote_state()['jobs'][self.job['claim_id']][1],'sent')
        self.assertIsNone(self.remote_state()['owner'])
        self.assertEqual(self.publisher(self.new_journal()).run(self.job,True),'already_sent')
        self.assertEqual(len(self.api.posts()),2)
    def test_failed_initial_checkpoint_prevents_api(self):
        with self.intercept_push(1):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(self.api.calls,[])
    def test_failed_create_intent_prevents_post(self):
        with self.intercept_push(2):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(self.api.posts(),[])
        self.assertIsNotNone(self.remote_state()['owner'])
    def test_container_checkpoint_failure_prevents_publish(self):
        with self.intercept_push(3):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),1)
        self.assertEqual(self.remote_state()['jobs'][self.job['claim_id']][1],'creating')
        fresh=self.new_journal();self.recover(fresh)
        self.assertEqual(self.publisher(fresh).run(self.job,True),'reconciliation_required')
        self.fails('creation_unknown_manual_review_required',lambda:self.publisher(fresh).reconcile(self.job['claim_id']))
        self.assertEqual(len(self.api.posts()),1)
    def test_publish_intent_failure_prevents_publish(self):
        with self.intercept_push(4):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),1)
        self.assertEqual(self.remote_state()['jobs'][self.job['claim_id']][1],'created')
    def test_lost_creation_intent_ack_never_posts(self):
        with self.intercept_push(2,after=True):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(self.api.posts(),[])
        fresh=self.new_journal();self.recover(fresh)
        self.assertEqual(self.publisher(fresh).run(self.job,True),'reconciliation_required')
        self.fails('creation_unknown_manual_review_required',lambda:self.publisher(fresh).reconcile(self.job['claim_id']))
    def test_known_container_resume_survives_runner_loss(self):
        self.api.status='IN_PROGRESS'
        self.fails('container_not_ready_reconcile',lambda:self.pub.run(self.job,True))
        fresh=self.new_journal();q=self.publisher(fresh);self.api.status='FINISHED'
        self.assertEqual(q.reconcile(self.job['claim_id']),'quarantined_ready')
        self.assertEqual(q.resume_created(self.job),'sent')
        self.assertEqual(len(self.api.posts()),2)
    def test_run_window_rechecked_after_remote_commit_latency(self):
        import datetime as dt
        original=self.j._checkpoint
        def slow(state):
            original(state)
            if any(r[1]=='publishing' for r in state['jobs'].values()):
                self.pub.clock=lambda:NOW+dt.timedelta(hours=2)
        self.j._checkpoint=slow
        self.fails('expired_run_window',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),1)
        self.assertEqual(self.remote_state()['jobs'][self.job['claim_id']][1],'publishing')
    def test_lost_intent_ack_remains_quarantined_after_restart(self):
        with self.intercept_push(4,after=True):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),1)
        self.assertEqual(self.remote_state()['jobs'][self.job['claim_id']][1],'publishing')
        fresh=self.new_journal();q=self.publisher(fresh)
        self.fails('remote_owner_requires_review',lambda:q.run(self.job,True))
        self.recover(fresh)
        self.assertEqual(q.reconcile(self.job['claim_id']),'quarantined_uncertain')
        self.fails('unsafe_resume',lambda:q.resume_created(self.job));self.assertEqual(len(self.api.posts()),1)
    def test_sent_checkpoint_failure_does_not_claim_success(self):
        with self.intercept_push(5):self.fails('durable_checkpoint_uncertain',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),2)
        fresh=self.new_journal();self.recover(fresh);q=self.publisher(fresh)
        self.assertEqual(q.run(self.job,True),'reconciliation_required')
        self.assertEqual(q.reconcile(self.job['claim_id']),'quarantined_uncertain')
        self.api.status='PUBLISHED';self.assertEqual(q.reconcile(self.job['claim_id']),'reconciled_sent')
        self.assertEqual(len(self.api.posts()),2)
    def test_publish_timeout_restart_never_retries(self):
        self.api.fail=('POST','123/media_publish')
        self.fails('publication_uncertain_reconcile',lambda:self.pub.run(self.job,True))
        q=self.publisher(self.new_journal())
        self.assertEqual(q.run(self.job,True),'reconciliation_required')
        self.assertEqual(q.reconcile(self.job['claim_id']),'quarantined_uncertain')
        self.fails('unsafe_resume',lambda:q.resume_created(self.job));self.assertEqual(len(self.api.posts()),2)
    def test_competing_jobs_one_wins_no_double_post(self):
        a,b=self.j,self.new_journal();barrier=threading.Barrier(2)
        for j in (a,b):
            original=j._git;counter=[0]
            def race(*args,_original=original,_counter=counter,**kwargs):
                if args[0]=='push':
                    _counter[0]+=1
                    if _counter[0]==1:barrier.wait(timeout=5)
                return _original(*args,**kwargs)
            j._git=race
        def run(j):
            try:return self.publisher(j).run(self.job,True)
            except p.Stop as e:return str(e)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(run,[a,b]))
        self.assertCountEqual(results,['sent','durable_checkpoint_uncertain'])
        self.assertEqual(len(self.api.posts()),2)
    def test_abandoned_owner_explicit_recovery_fences_old_runner(self):
        ctx=self.j.exclusive();ctx.__enter__()
        fresh=self.new_journal();head,state=fresh.inspect()
        self.fails('stop_original_runner_first',lambda:fresh.recover_abandoned_owner(head,state['owner']))
        self.recover(fresh)
        self.fails('durable_checkpoint_uncertain',lambda:self.j.save(self.job['claim_id'],'a'*64,'creating',NOW))
        self.assertEqual(self.api.posts(),[])
        ctx.__exit__(None,None,None)
    def test_recovery_rejects_stale_head(self):
        ctx=self.j.exclusive();ctx.__enter__();fresh=self.new_journal();head,state=fresh.inspect()
        self.j.save(self.job['claim_id'],'a'*64,'creating',NOW)
        self.fails('recovery_head_or_owner_changed',lambda:fresh.recover_abandoned_owner(head,state['owner'],stopped_confirmed=True))
        ctx.__exit__(None,None,None)
    def test_missing_remote_branch_fails_closed(self):
        git(self.remote,'update-ref','-d',REF)
        self.fails('git_operation_failed',lambda:self.new_journal());self.assertEqual(self.api.posts(),[])
    def test_wrong_genesis_fails_closed(self):
        self.fails('git_operation_failed',lambda:GitJournal(self.remote,'a'*40))
    def test_no_network_transport_allowed(self):
        self.fails('local_bare_remote_required',lambda:GitJournal('https://github.com/owner/repo.git',self.genesis))
    def test_dry_run_does_not_touch_remote(self):
        with patch.object(self.j,'exclusive',side_effect=AssertionError('must stay offline')):
            self.assertEqual(self.pub.run(self.job),'dry_run_validated_no_network')
        self.assertEqual(self.remote_state()['jobs'],{})
