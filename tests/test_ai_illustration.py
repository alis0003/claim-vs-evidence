import hashlib
import unittest
import publisher as p
from test_publisher import job, NOW, iso, fetch

class AIIllustration(unittest.TestCase):
    def candidate(self):
        j=job();j.pop('screenshot_provenance')
        j['caption']='A verified narrow claim. AI illustration, not actual footage. Sources: https://www.nasa.gov/fact'
        j['visual_provenance']=dict(kind='ai_illustration',display_label='AI illustration, not actual footage',
            generator='Mock generator',generation_reference='mock-only',consent_basis='User approved original labelled illustration',
            generation_prompt='Original stylized polar bear illustration, no real event recreation or supplied images.',
            generation_record_url='https://raw.githubusercontent.com/owner/repo/commit/sources/generation.json',
            generated_asset_url='https://raw.githubusercontent.com/owner/repo/commit/cards/original.png',
            asset_sha256=hashlib.sha256(b'mocked-original-png').hexdigest(),generated_at=iso(-1),
            context='Generic symbolic illustration only',transformations='Fit full image in card',user_approved=True,
            claim_presented_as_text=True,third_party_inputs_used=False,input_assets=[],derived_from_denied_material=False,
            not_event_evidence=True,facts_independently_sourced=True,actual_event_reconstruction=False,
            visual_review=dict(label_visible=True,context_verified=True,reviewer_id=j['reviewer'],
                jpeg_sha256=j['image']['sha256'],caption_sha256=hashlib.sha256(j['caption'].encode()).hexdigest(),
                reviewed_at=iso(-1),notes='Mock independent exact output review'))
        return j
    def reject(self,j,code):
        with self.assertRaisesRegex(p.Stop,'^'+code+'$'):p.validate_ready(j,NOW)
    def test_original_labelled_illustration(self):p.validate_ready(self.candidate(),NOW)
    def test_label_required_on_card_and_caption(self):
        j=self.candidate();j['visual_provenance']['display_label']='Evidence photo';self.reject(j,'missing_ai_disclosure')
        j=self.candidate();j['caption']='Unlabelled claim';self.reject(j,'missing_ai_disclosure')
    def test_real_evidence_claim_forbidden(self):
        for key,val in [('not_event_evidence',False),('facts_independently_sourced',False),('actual_event_reconstruction',True)]:
            j=self.candidate();j['visual_provenance'][key]=val;self.reject(j,'ai_presented_as_evidence')
    def test_denied_or_third_party_inputs_forbidden(self):
        for key,val in [('third_party_inputs_used',True),('derived_from_denied_material',True),('input_assets',['denied-image'])]:
            j=self.candidate();j['visual_provenance'][key]=val;self.reject(j,'unapproved_generation_inputs')
    def test_missing_user_approval(self):
        j=self.candidate();j['visual_provenance']['user_approved']=False;self.reject(j,'unapproved_ai_illustration')
    def test_no_false_public_domain_or_capture(self):
        for key,val in [('license_exact','public-domain'),('photo_captured_at',iso(-1))]:
            j=self.candidate();j['visual_provenance'][key]=val;self.reject(j,'misleading_ai_provenance')
    def test_claim_recency_unchanged(self):
        j=self.candidate();j['claim_date']=iso(-24*31);self.reject(j,'stale_or_future_evidence')
    def test_generation_future_timestamp(self):
        j=self.candidate();j['visual_provenance']['generated_at']=iso(1);self.reject(j,'stale_or_future_evidence')
    def test_final_bytes_binding(self):
        j=self.candidate();j['image']['sha256']='f'*64;self.reject(j,'unbound_visual_review')
    def test_no_screenshot_record(self):
        j=self.candidate();j['screenshot_provenance']=job()['screenshot_provenance'];self.reject(j,'ai_mislabeled_as_screenshot')
    def test_anonymous_preflight_checks_generation_original(self):
        j=self.candidate()
        def original(url,**kwargs):
            if url.endswith('generation.json'):return 'application/json',b'{"generation": "mock independently reviewed metadata"}'
            if url.endswith('original.png'):return 'image/png',b'mocked-original-png'
            return fetch(url,**kwargs)
        p.preflight(j,original,NOW)
        def changed(url,**kwargs):
            if url.endswith('original.png'):return 'image/png',b'wrong bytes'
            return original(url,**kwargs)
        with self.assertRaisesRegex(p.Stop,'generated_asset_mismatch'):p.preflight(j,changed,NOW)

    def test_honest_completion_observation(self):
        j=self.candidate();v=j['visual_provenance'];v.update(generated_at=None,generation_time_basis='completion_observed',
            generation_time_note='Output observed complete at this time; exact generation event unrecorded.',generation_completed_by=iso(-1))
        p.validate_ready(j,NOW)
        v.pop('generation_time_note');self.reject(j,'missing_evidence')
    def test_em_dash_disclosure(self):
        j=self.candidate();v=j['visual_provenance'];v['display_label']='AI illustration — not actual footage'
        j['caption']=j['caption'].replace('AI illustration, not actual footage',v['display_label'])
        v['visual_review']['caption_sha256']=hashlib.sha256(j['caption'].encode()).hexdigest();p.validate_ready(j,NOW)
