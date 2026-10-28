import copy
import unittest
import publisher as p
from test_publisher import job, NOW, iso

class SourceRoles(unittest.TestCase):
    def setUp(self):
        self.job=job()
        self.job['sources'][0].update(evidence_role='recent_fact_check', independent_fact_check=True)
        self.doc=dict(url='https://github.com/vendor/project/security/advisories/GHSA-test',
            title='Original advisory',publisher='Vendor',supports='Documentary identity and scope',
            published_date='2026-04-23',checked_at=iso(-1),supports_claim_analysis=True,
            evidence_role='primary_documentary',primary_source=True,publication_date_verified=True,
            publication_date_basis='Displayed publication date independently checked',
            documentary_relevance='Older authentic document contradicts the current claim')
        self.job['sources'].append(self.doc)
    def rejects(self, reason):
        with self.assertRaisesRegex(p.Stop, '^'+reason+'$'):
            p.validate(self.job,NOW)
    def test_old_primary_with_recent_fact_check(self):
        p.validate(self.job,NOW)
        self.assertEqual(self.doc['published_date'],'2026-04-23')
    def test_old_primary_alone_fails(self):
        self.job['sources']=[self.doc];self.rejects('missing_recent_evidence')
    def test_recent_ordinary_report_not_independent_fact_check(self):
        self.job['sources'][0]['evidence_role']='recent_reporting'
        self.rejects('documentary_requires_recent_fact_check')
    def test_unverified_primary_fails(self):
        self.doc['publication_date_verified']=False;self.rejects('unverified_documentary_source')
    def test_stale_fact_check_fails(self):
        self.job['sources'][0]['published_at']=iso(-24*31)
        self.rejects('stale_or_future_evidence')
    def test_stale_claim_fails_even_with_new_review(self):
        self.job['claim_date']=iso(-24*31);self.rejects('stale_or_future_evidence')
    def test_stale_document_check_fails(self):
        self.doc['checked_at']=iso(-24*8);self.rejects('stale_or_future_evidence')
    def test_future_document_date_fails(self):
        self.doc['published_date']='2026-10-28';self.rejects('source_checked_before_publication')
    def test_future_check_fails(self):
        self.doc['checked_at']=iso(1);self.rejects('stale_or_future_evidence')
    def test_two_publication_dates_fail(self):
        self.doc['published_at']=iso(-1);self.rejects('ambiguous_source_date')
    def test_check_precedes_publication_timestamp(self):
        self.job['sources'][0]['published_at']=iso(-.5)
        self.rejects('source_checked_before_publication')
    def test_date_only_circulation_keeps_precision(self):
        source=self.job['sources'][0];source.pop('published_at');source['published_date']='2026-10-26'
        self.job.update(claim_date=None,claim_date_basis='dated_fact_check_documents_circulation',
            claim_date_note='Post timestamp unknown; date is circulation by report',
            circulation_observed_date='2026-10-26',circulation_evidence_url=source['url'])
        p.validate(self.job,NOW)
    def test_document_cannot_supply_circulation(self):
        self.doc['published_date']='2026-10-26'
        self.job.update(claim_date=None,claim_date_basis='dated_fact_check_documents_circulation',
            claim_date_note='Cannot use documentary publication as circulation',
            circulation_observed_date='2026-10-26',circulation_evidence_url=self.doc['url'])
        self.rejects('unbound_circulation_evidence')
    def test_invalid_calendar_date(self):
        self.doc['published_date']='2026-02-30';self.rejects('invalid_source_date')
    def test_unknown_role(self):
        self.doc['evidence_role']='timeless';self.rejects('invalid_source_role')
