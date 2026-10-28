import copy
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import publisher as p

NOW=dt.datetime(2026,10,27,12,tzinfo=p.UTC)
def iso(delta=0): return (NOW+dt.timedelta(hours=delta)).isoformat()
def jpeg():
    return b'\xff\xd8\xff\xc0'+struct.pack('>H B H H B',17,8,1080,1080,3)+b'\x01\x11\x00\x02\x11\x00\x03\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x01\xff\xd9'
def legacy_job():
    return dict(claim='A testable claim for mocked tests',claim_id=p.claim_id('A testable claim for mocked tests'),
      review_provenance=dict(mode='independent_automated',producer_id='test-producer',reviewer_id='test-editor',review_notes='Separate review of evidence, scope and semantic duplicates'),
      caption='A reviewed explanation. Sources: https://www.nasa.gov/fact',reviewer='test-editor',evidence_summary='Verified against original evidence',
      ready_for_publish=True,editorial_verified=True,evidence_supported=True,high_impact_identifiable_person=False,verdict='true',language='en',
      claim_date=iso(-24),reviewed_at=iso(-1),created_at=iso(-2),expires_at=iso(24),run_after=iso(-1),run_before=iso(1),
      sources=[dict(url='https://www.nasa.gov/fact',title='Original report',publisher='Source',supports='Context of claim',published_at=iso(-24),checked_at=iso(-1),supports_claim_analysis=True)],
      screenshot_provenance=dict(original=True,rights_reviewed=True,publisher='Original publisher',context='Original post and capture context',original_url='https://www.nasa.gov/original',captured_at=iso(-24),sha256='a'*64),
      image=dict(url='https://raw.githubusercontent.com/owner/repo/main/card.jpg',mime='image/jpeg',width=1080,height=1080,sha256=hashlib.sha256(jpeg()).hexdigest()))
def job():
    j=legacy_job()
    j['caption'] += ' Claim screenshot. Credit: Test creator. CC-BY-4.0.'
    j['visual_provenance']=dict(kind='claim_screenshot',source_url=j['screenshot_provenance']['original_url'],
        license_url='https://creativecommons.org/licenses/by/4.0/',rights_evidence_url='https://www.nasa.gov/rights',
        creator='Test creator',attribution='Credit: Test creator. CC-BY-4.0.',license_exact='CC-BY-4.0',
        rights_basis='Mocked explicit licence statement on original source',transformations='Crop and resize',context='Mock original claim',
        reuse_rights_verified=True,social_publication_permitted=True,adaptation_permitted=True,rights_checked_at=iso(-1),
        asset_sha256=j['screenshot_provenance']['sha256'],display_label='Claim screenshot',
        visual_review=dict(label_visible=True,context_verified=True,reviewer_id=j['reviewer'],jpeg_sha256=j['image']['sha256'],
                          caption_sha256=hashlib.sha256(j['caption'].encode()).hexdigest(),reviewed_at=iso(-1),notes='Mock independent pixel review'))
    return j
def fetch(url,**kwargs):
    return ('image/jpeg',jpeg()) if url.endswith('.jpg') else ('text/html',b'Original factual report with readable source content. '*5)
class API:
    def __init__(self):
        self.calls=[];self.username=p.USERNAME;self.usage=0;self.fail=None;self.status='FINISHED';self.bad_create=False
    def call(self,method,path,**fields):
        self.calls.append((method,path,fields))
        if self.fail==(method,path): raise TimeoutError('secret-token Authorization: Bearer secret-token')
        if path=='me': return dict(username=self.username,user_id='123')
        if path.endswith('/content_publishing_limit'): return dict(data=[dict(quota_usage=self.usage,config=dict(quota_total=100,quota_duration=86400))])
        if path=='123/media': return {} if self.bad_create else dict(id='456')
        if path=='123/media_publish': return dict(id='789')
        return dict(status_code=self.status)
    def posts(self): return [c for c in self.calls if c[0]=='POST']
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'journal.sqlite';self.j=p.Journal(self.path);self.api=API();self.pub=p.Publisher(self.j,self.api,fetch,lambda:NOW);self.job=job()
    def tearDown(self): self.j.db.close();self.tmp.cleanup()
    def fails(self,code,fn):
        with self.assertRaisesRegex(p.Stop,'^'+code+'$'): fn()
    def test_dry_run_no_network(self):
        self.assertEqual(self.pub.run(self.job),'dry_run_validated_no_network');self.assertEqual(self.api.calls,[])
    def test_sent_duplicate(self):
        self.assertEqual(self.pub.run(self.job,True),'sent');self.assertEqual(self.pub.run(self.job,True),'already_sent');self.assertEqual(len(self.api.posts()),2)
    def test_expired(self):
        self.job['expires_at']=iso(-1);self.fails('expired_job',lambda:self.pub.run(self.job,True));self.assertFalse(self.api.calls)
    def test_expired_window(self):
        self.job['run_before']=iso(-.5);self.fails('expired_run_window',lambda:self.pub.run(self.job,True))
    def test_wrong_identity(self):
        self.api.username='someone_else';self.fails('wrong_identity',lambda:self.pub.run(self.job,True));self.assertFalse(self.api.posts())
    def test_missing_token(self): self.fails('missing_token',lambda:p.Instagram(''))
    def test_missing_evidence(self):
        for key,value in [('sources',[]),('editorial_verified',False),('evidence_supported',False),('high_impact_identifiable_person',True),('screenshot_provenance',{}),('verdict','FAKE')]:
            with self.subTest(key=key):
                item=copy.deepcopy(self.job);item[key]=value
                with self.assertRaises(p.Stop): p.validate(item,NOW)
    def test_stale_source(self):
        self.job['sources'][0]['published_at']=iso(-24*31);self.fails('stale_or_future_evidence',lambda:p.validate(self.job,NOW))
    def test_quota(self):
        self.api.usage=10;self.fails('quota_exhausted',lambda:self.pub.run(self.job,True));self.assertFalse(self.api.posts())
    def test_quota_unreadable(self):
        self.api.usage='0';self.fails('unreadable_quota',lambda:self.pub.run(self.job,True))
    def test_failed_creation(self):
        self.api.fail=('POST','123/media');self.fails('creation_uncertain_reconcile',lambda:self.pub.run(self.job,True))
        self.assertEqual(self.pub.run(self.job,True),'reconciliation_required');self.assertEqual(len(self.api.posts()),1)
        self.fails('creation_unknown_manual_review_required',lambda:self.pub.reconcile(self.job['claim_id']))
    def test_ambiguous_creation(self):
        self.api.bad_create=True;self.fails('creation_uncertain_reconcile',lambda:self.pub.run(self.job,True));self.assertEqual(self.j.row(self.job['claim_id'])[1],'creating')
    def test_failed_publish_recovery(self):
        self.api.fail=('POST','123/media_publish');self.fails('publication_uncertain_reconcile',lambda:self.pub.run(self.job,True))
        self.assertEqual(self.j.row(self.job['claim_id'])[3],'456')
        self.j.db.close();self.j=p.Journal(self.path);self.pub=p.Publisher(self.j,self.api,fetch,lambda:NOW)
        self.assertEqual(self.pub.run(self.job,True),'reconciliation_required')
        self.assertEqual(self.pub.reconcile(self.job['claim_id']),'quarantined_uncertain')
        self.api.status='PUBLISHED';self.assertEqual(self.pub.reconcile(self.job['claim_id']),'reconciled_sent');self.assertEqual(len(self.api.posts()),2)
    def test_container_not_ready(self):
        self.api.status='IN_PROGRESS';self.fails('container_not_ready_reconcile',lambda:self.pub.run(self.job,True));self.assertEqual(self.j.row(self.job['claim_id'])[1],'created');self.assertEqual(len(self.api.posts()),1)
    def test_safe_resume_created(self):
        self.api.status='IN_PROGRESS'
        self.fails('container_not_ready_reconcile',lambda:self.pub.run(self.job,True))
        self.api.status='FINISHED'
        self.assertEqual(self.pub.reconcile(self.job['claim_id']),'quarantined_ready')
        self.assertEqual(self.pub.resume_created(self.job),'sent')
        self.assertEqual(len(self.api.posts()),2)
    def test_unsafe_resume_publish_timeout(self):
        self.api.fail=('POST','123/media_publish')
        self.fails('publication_uncertain_reconcile',lambda:self.pub.run(self.job,True))
        self.fails('unsafe_resume',lambda:self.pub.resume_created(self.job))
        self.assertEqual(len(self.api.posts()),2)
    def test_readiness_polling_is_get_only_and_bounded(self):
        original=self.api.call;statuses=iter(['IN_PROGRESS','FINISHED']);waits=[]
        def status(method,path,**fields):
            if method=='GET' and path=='456':
                self.api.calls.append((method,path,fields));return {'status_code':next(statuses)}
            return original(method,path,**fields)
        self.api.call=status;self.pub.readiness_checks=5;self.pub.sleeper=waits.append
        self.assertEqual(self.pub.run(self.job,True),'sent')
        self.assertEqual(waits,[60]);self.assertEqual(len(self.api.posts()),2)
    def test_readiness_polling_never_repeats_creation(self):
        self.api.status='IN_PROGRESS';self.pub.readiness_checks=5;waits=[];self.pub.sleeper=waits.append
        self.fails('container_not_ready_reconcile',lambda:self.pub.run(self.job,True))
        self.assertEqual(waits,[60]*4);self.assertEqual(len(self.api.posts()),1)
    def test_network_timeout_before_creation(self):
        self.api.fail=('GET','me')
        with self.assertRaises(TimeoutError): self.pub.run(self.job,True)
        self.assertIsNone(self.j.row(self.job['claim_id']));self.assertFalse(self.api.posts())
    def test_transport_redaction(self):
        with patch.object(p.PinnedHTTPS,'request',side_effect=TimeoutError('secret-token Authorization: Bearer secret-token')):
            self.fails('transport_timeout',lambda:p.Instagram('secret-token').call('GET','me'))
    def test_safe_http_status_diagnostics_no_response_leak(self):
        from unittest.mock import Mock
        for status,code in [(301,'http_redirect_301'),(403,'http_denied_403'),(407,'http_proxy_auth_407'),(429,'http_rate_limited_429'),(500,'http_status_500')]:
            response=Mock(status=status);response.read.side_effect=AssertionError('must not read denial body')
            with patch.object(p.PinnedHTTPS,'request'),patch.object(p.PinnedHTTPS,'getresponse',return_value=response):
                self.fails(code,lambda:p.Instagram('secret-token').call('GET','me'))
                response.read.assert_not_called()
    def test_transport_classification_does_not_echo_exception(self):
        failures=[(p.socket.gaierror('secret'), 'dns_failure'),(p.ssl.SSLError('secret'),'tls_failure'),(PermissionError('secret'),'network_permission_denied'),(ConnectionRefusedError('secret'),'connection_refused'),(ConnectionResetError('secret'),'connection_reset')]
        for error,code in failures:
            with patch.object(p.PinnedHTTPS,'request',side_effect=error):
                self.fails(code,lambda:p.Instagram('secret-token').call('GET','me'))
    def test_changed_job(self):
        self.pub.run(self.job,True);self.job['caption']+=' Changed';self.job['visual_provenance']['visual_review']['caption_sha256']=hashlib.sha256(self.job['caption'].encode()).hexdigest();self.fails('changed_job',lambda:self.pub.run(self.job,True))
    def test_rolling_limit_and_spacing(self):
        for i in range(10): self.j.save(str(i),'fp','sent',NOW-dt.timedelta(hours=2+i))
        self.fails('rolling_limit',lambda:self.pub.run(self.job,True))
    def test_spacing(self):
        self.j.save('other','fp','sent',NOW-dt.timedelta(minutes=30));self.fails('spacing_limit',lambda:self.pub.run(self.job,True))
    def test_all_new_jobs_blocked_on_unknown(self):
        self.j.save('other','fp','creating',NOW-dt.timedelta(days=2));self.fails('reconciliation_required',lambda:self.pub.run(self.job,True))
    def test_unsafe_urls(self):
        for url in ['http://www.nasa.gov/x','https://127.0.0.1/a','https://169.254.169.254/a','https://[::1]/a','https://example.com/x','https://me:password@www.nasa.gov/a','https://www.nasa.gov/a?token=secret','https://x.local/a']:
            with self.subTest(url=url),self.assertRaises(p.Stop): p.public_url(url)
    def test_unknown_post_date_uses_dated_circulation_evidence(self):
        self.job.update(claim_date=None,claim_date_basis='dated_fact_check_documents_circulation',
            circulation_observed_date=(NOW-dt.timedelta(days=1)).date().isoformat(),
            circulation_evidence_url=self.job['sources'][0]['url'],
            claim_date_note='Fact check documents circulation by publication date; actual post date unknown.')
        p.validate(self.job,NOW)
        self.assertIsNone(self.job['claim_date'])
        self.job['circulation_evidence_url']='https://www.nasa.gov/unrelated'
        with self.assertRaisesRegex(p.Stop,'unbound_circulation_evidence'):p.validate(self.job,NOW)
    def test_unknown_post_date_without_basis_rejected(self):
        self.job['claim_date']=None
        with self.assertRaisesRegex(p.Stop,'missing_claim_date_basis'):p.validate(self.job,NOW)
    def test_stale_circulation_evidence_rejected(self):
        self.job.update(claim_date=None,claim_date_basis='dated_fact_check_documents_circulation',
            circulation_observed_date=(NOW-dt.timedelta(days=31)).date().isoformat(),
            circulation_evidence_url=self.job['sources'][0]['url'],claim_date_note='Post date unknown')
        with self.assertRaisesRegex(p.Stop,'stale_or_future_evidence'):p.validate(self.job,NOW)
    def test_source_query_preserved_and_media_query_denied(self):
        url='https://perma.cc/8X4Q-5YPQ?type=image'
        self.assertEqual(p.public_url(url,allow_source_query=True).query,'type=image')
        with self.assertRaises(p.Stop):p.public_url(url)
        self.job['sources'][0]['url']=url
        self.job['screenshot_provenance']['original_url']=url;self.job['visual_provenance']['source_url']=url
        p.validate(self.job,NOW)
        calls=[]
        def recording(url,**kwargs):
            calls.append((url,kwargs));return fetch(url,**kwargs)
        p.preflight(self.job,recording)
        self.assertEqual(calls[0][0],url);self.assertTrue(calls[0][1]['source'])
    def test_honest_filesystem_save_time_without_capture_timestamp(self):
        provenance=self.job['screenshot_provenance']
        provenance.update(captured_at=None,saved_at_utc=iso(-2),
            timestamp_basis='filesystem_save_exact_capture_unrecorded',
            timestamp_note='Exact capture event was not recorded; saved_at_utc is the filesystem save time only.')
        p.validate(self.job,NOW)
        provenance['saved_at_utc']=iso(-24*31)
        with self.assertRaisesRegex(p.Stop,'stale_or_future_evidence'):p.validate(self.job,NOW)
    def test_missing_capture_requires_explicit_save_time_basis(self):
        provenance=self.job['screenshot_provenance'];provenance['captured_at']=None
        with self.assertRaises(p.Stop):p.validate(self.job,NOW)
        provenance.update(saved_at_utc=iso(-2),timestamp_note='approximate',timestamp_basis='capture')
        with self.assertRaisesRegex(p.Stop,'missing_provenance_time_basis'):p.validate(self.job,NOW)
    def test_source_queries_cannot_hide_credentials_or_redirects(self):
        for q in ['access_token=secret','token=secret','sig=secret','redirect=https%3A%2F%2F127.0.0.1','q=https%3A%2F%2F127.0.0.1','type=image&type=video','type=%250a','type=image%0a','key=secret']:
            with self.subTest(q=q),self.assertRaises(p.Stop):
                p.public_url('https://perma.cc/8X4Q-5YPQ?'+q,allow_source_query=True)
        for url in ['https://127.0.0.1/x?type=image','https://u:p@perma.cc/x?type=image']:
            with self.assertRaises(p.Stop):p.public_url(url,allow_source_query=True)
    def test_independent_automated_review_required(self):
        for review in [None,dict(mode='human'),dict(mode='independent_automated',producer_id='test-editor',reviewer_id='test-editor',review_notes='same producer')]:
            item=copy.deepcopy(self.job);item['review_provenance']=review
            with self.assertRaisesRegex(p.Stop,'missing_independent_review'):p.validate(item,NOW)
    def test_private_dns(self):
        with patch.object(p.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            self.fails('unsafe_dns',lambda:p.request('https://www.nasa.gov/fact'))
    def test_image_and_source(self):
        p.preflight(self.job,fetch)
        self.fails('unreadable_source',lambda:p.preflight(self.job,lambda url,**k:('text/html',b'') if url==self.job['sources'][0]['url'] else fetch(url,**k)))
        self.job['image']['width']=1000;self.fails('media_mismatch',lambda:p.preflight(self.job,fetch))
    def test_unsupported_media(self):
        for raw in [b'PNG',b'\xff\xd8\xff\xd9']:
            with self.assertRaises(p.Stop):p.jpeg_dimensions(raw)
    def test_window_expiry_during_fetch(self):
        def late(*args,**kw): self.pub.clock=lambda:NOW+dt.timedelta(hours=2);return fetch(*args,**kw)
        self.pub.fetch=late;self.fails('expired_run_window',lambda:self.pub.run(self.job,True));self.assertFalse(self.api.posts())
    def test_window_expiry_during_final_quota(self):
        original=self.api.call
        def delayed(method,path,**fields):
            result=original(method,path,**fields)
            if path.endswith('content_publishing_limit') and self.j.row(self.job['claim_id']):
                self.pub.clock=lambda:NOW+dt.timedelta(hours=2)
            return result
        self.api.call=delayed
        self.fails('expired_run_window',lambda:self.pub.run(self.job,True))
        self.assertEqual(len(self.api.posts()),1)
    def test_cli_redacts_bad_queue(self):
        path=Path(self.tmp.name)/'bad.json';path.write_text('[{"token":"secret-token"}]')
        with patch.object(p.sys,'argv',['publisher.py',str(path)]), patch.object(p.sys,'stderr',new_callable=io.StringIO) as err:
            self.assertEqual(p.main(),1)
            self.assertNotIn('secret-token',err.getvalue())
            self.assertNotIn('Authorization',err.getvalue())
    def test_duplicate_queue_rejected(self):
        path=Path(self.tmp.name)/'queue.json';path.write_text(json.dumps([self.job,self.job]))
        # Separate fixture time from the real system clock for offline CLI checks.
        with patch.object(p.sys,'argv',['publisher.py',str(path)]), patch.object(p,'validate',return_value=self.job['claim_id']), patch.object(p.sys,'stderr',new_callable=io.StringIO):
            self.assertEqual(p.main(),1)
    def test_publication_intent_is_durable(self):
        original=self.api.call
        def spy(method,path,**fields):
            if method=='POST':
                row=self.j.row(self.job['claim_id'])
                self.assertEqual(row[1],'creating' if path.endswith('/media') else 'publishing')
                if path.endswith('media_publish'):self.assertEqual(row[3],'456')
            return original(method,path,**fields)
        self.api.call=spy;self.pub.run(self.job,True)

if __name__=='__main__':unittest.main()
