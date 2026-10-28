import copy
import datetime as dt
import unittest
import publisher as p
from test_publisher import job,NOW

class QueueHistoryTests(unittest.TestCase):
    def test_expired_window_retained_but_not_due(self):
        j=job();snapshot=copy.deepcopy(j)
        self.assertEqual(p.select_due([j],NOW+dt.timedelta(hours=2)),[])
        self.assertEqual(j,snapshot)
        with self.assertRaisesRegex(p.Stop,'expired_run_window'):p.validate(j,NOW+dt.timedelta(hours=2))
    def test_expired_job_retained(self):
        self.assertEqual(p.select_due([job()],NOW+dt.timedelta(days=31)),[])
    def test_future_job_not_due(self):
        self.assertEqual(p.select_due([job()],NOW-dt.timedelta(hours=3)),[])
    def test_duplicate_historical_id_still_rejected(self):
        with self.assertRaisesRegex(p.Stop,'duplicate_claim'):
            p.select_due([job(),job()],NOW+dt.timedelta(days=31))
    def test_historical_id_mismatch_rejected(self):
        j=job();j['claim_id']='a'*64
        with self.assertRaisesRegex(p.Stop,'invalid_claim_id'):p.select_due([j],NOW+dt.timedelta(days=31))
    def test_due_job_still_requires_fresh_evidence(self):
        j=job();j['sources'][0]['checked_at']=(NOW-dt.timedelta(days=8)).isoformat()
        with self.assertRaisesRegex(p.Stop,'stale_or_future_evidence'):p.select_due([j],NOW)
    def test_due_job_still_requires_editorial_verification(self):
        j=job();j['editorial_verified']=False
        with self.assertRaisesRegex(p.Stop,'unverified_editorial'):p.select_due([j],NOW)
    def test_invalid_historical_window_rejected(self):
        j=job();j['run_before']=j['run_after']
        with self.assertRaisesRegex(p.Stop,'invalid_queue_window'):p.select_due([j],NOW+dt.timedelta(days=31))
