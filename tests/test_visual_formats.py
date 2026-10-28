import copy
import hashlib
import tempfile
import unittest
import publisher as p
from test_publisher import job, legacy_job, NOW, iso, API, fetch

class VisualFormats(unittest.TestCase):
    def photo(self):
        j=job();j.pop('screenshot_provenance');v=j['visual_provenance']
        j['caption']=j['caption'].replace('Claim screenshot','Illustrative photo')
        v.update(kind='evidence_photo',display_label='Illustrative photo',claim_presented_as_text=True,
                 acquired_at=iso(-1),photo_captured_at=None,capture_date_note='Original exposure date unknown; acquisition is not exposure.')
        v['visual_review']['caption_sha256']=hashlib.sha256(j['caption'].encode()).hexdigest()
        return j
    def rejects(self,j,reason):
        with self.assertRaisesRegex(p.Stop,'^'+reason+'$'):p.validate_ready(j,NOW)
    def test_licensed_screenshot(self):p.validate_ready(job(),NOW)
    def test_licensed_illustration(self):p.validate_ready(self.photo(),NOW)
    def test_licensed_evidence_photo_needs_connection(self):
        j=self.photo();v=j['visual_provenance'];v['display_label']='Evidence photo'
        j['caption']=j['caption'].replace('Illustrative photo','Evidence photo')
        v['visual_review']['caption_sha256']=hashlib.sha256(j['caption'].encode()).hexdigest()
        v['evidentiary_connection']='Reviewed source establishes what is depicted'
        v['evidence_source_url']=j['sources'][0]['url'];p.validate_ready(j,NOW)
        v['evidence_source_url']='https://www.nasa.gov/unrelated';self.rejects(j,'unbound_photo_evidence')
    def test_unknown_rights_fail(self):
        for key in ('reuse_rights_verified','social_publication_permitted','adaptation_permitted'):
            j=self.photo();j['visual_provenance'][key]=False;self.rejects(j,'unverified_visual_rights')
    def test_unsupported_license(self):
        j=self.photo();j['visual_provenance']['license_exact']='found online';self.rejects(j,'unsupported_visual_license')
    def test_photo_cannot_claim_screenshot(self):
        j=self.photo();j['visual_provenance']['display_label']='Claim screenshot';self.rejects(j,'misleading_visual_label')
    def test_photo_cannot_keep_screenshot_record(self):
        j=self.photo();j['screenshot_provenance']=job()['screenshot_provenance'];self.rejects(j,'photo_mislabeled_as_screenshot')
    def test_missing_attribution(self):
        j=self.photo();j['caption']='Illustrative photo';self.rejects(j,'missing_visual_attribution')
    def test_visual_review_bound_to_bytes(self):
        j=self.photo();j['image']['sha256']='f'*64;self.rejects(j,'unbound_visual_review')
    def test_visual_review_bound_to_caption(self):
        j=self.photo();j['caption']+=' Edited';self.rejects(j,'unbound_visual_review')
    def test_stale_rights_check(self):
        j=self.photo();j['visual_provenance']['rights_checked_at']=iso(-24*8);self.rejects(j,'stale_or_future_evidence')
    def test_claim_freshness_unchanged(self):
        j=self.photo();j['claim_date']=iso(-24*31);self.rejects(j,'stale_or_future_evidence')
    def test_sharealike_terms_required(self):
        j=self.photo();j['visual_provenance']['license_exact']='CC-BY-SA-4.0';self.rejects(j,'missing_sharealike_terms')
    def test_future_photo_capture(self):
        j=self.photo();j['visual_provenance']['photo_captured_at']=iso(1);self.rejects(j,'future_photo_capture')
    def test_legacy_readable_but_not_new_publication(self):
        j=legacy_job();p.validate(j,NOW);self.rejects(j,'licensed_visual_required')
        with tempfile.TemporaryDirectory() as d:
            journal=p.Journal(d+'/state.db');api=API();pub=p.Publisher(journal,api,fetch,lambda:NOW)
            with self.assertRaisesRegex(p.Stop,'licensed_visual_required'):pub.run(j,True)
            self.assertEqual(api.calls,[]);journal.db.close()
    def test_rights_metadata_unreadable(self):
        j=self.photo()
        def unavailable(url,**kwargs):
            return ('text/html',b'') if url==j['visual_provenance']['license_url'] else fetch(url,**kwargs)
        with self.assertRaisesRegex(p.Stop,'unreadable_rights_metadata'):p.preflight(j,unavailable)
