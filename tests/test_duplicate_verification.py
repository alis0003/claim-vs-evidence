import copy
import hashlib
import json
import unittest
import publisher as p
from test_publisher import job,NOW
from verify_duplicate import verify

class DuplicateVerificationTests(unittest.TestCase):
    def setUp(self):
        self.job=job()
        fingerprint=hashlib.sha256(json.dumps(self.job,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.state={'version':1,'owner':None,'jobs':{self.job['claim_id']:[fingerprint,'sent',NOW.isoformat(),'456','789']}}
    def test_sent_exact_job_no_api_or_state_calls(self):
        self.assertEqual(verify(self.job,self.state,NOW),'already_sent; zero API calls; zero state writes')
    def test_uncertain_state_cannot_pass(self):
        for phase in ['creating','created','publishing']:
            state=copy.deepcopy(self.state);state['jobs'][self.job['claim_id']][1]=phase
            with self.assertRaisesRegex(p.Stop,'publication_not_confirmed'):verify(self.job,state,NOW)
    def test_changed_job_cannot_pass(self):
        self.job['caption']='Changed after publish'
        with self.assertRaisesRegex(p.Stop,'changed_job'):verify(self.job,self.state,NOW)
    def test_held_owner_cannot_pass(self):
        self.state['owner']='a'*32
        with self.assertRaisesRegex(p.Stop,'owner_still_held'):verify(self.job,self.state,NOW)
    def test_missing_media_id_not_confirmed(self):
        self.state['jobs'][self.job['claim_id']][4]=None
        with self.assertRaisesRegex(p.Stop,'publication_not_confirmed'):verify(self.job,self.state,NOW)
