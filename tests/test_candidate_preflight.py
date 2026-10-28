import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from candidate_preflight import run, Stop, UTC

class CandidatePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'drafts/test').mkdir(parents=True)
        self.name='drafts/test/candidate.json';self.path=self.root/self.name
        self.path.write_text('{"sources": []}')
        self.validator=Mock();self.fetch=Mock();self.now=dt.datetime.now(UTC)
        self.registry={'candidates':{self.name:{'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'approved_for_anonymous_preflight':True,'review_record':'sources/review.json'}}}
    def call(self,name=None):
        return run(self.root,name or self.name,self.registry,self.now,self.validator,self.fetch)
    def test_allowed_once(self):
        self.assertIn('passed',self.call());self.validator.assert_called_once();self.fetch.assert_called_once()
    def test_unsafe_paths(self):
        for p in ['../queue.json','queue.json','/tmp/candidate.json','drafts/../sources/a.json','drafts/a.json;echo hi','drafts/$(id).json','drafts/a\nb.json','drafts//a.json']:
            with self.subTest(p=p),self.assertRaises(Stop):self.call(p)
        self.fetch.assert_not_called()
    def test_not_allowlisted(self):
        self.registry['candidates']={}
        with self.assertRaisesRegex(Stop,'not_review_allowlisted'):self.call()
        self.fetch.assert_not_called()
    def test_changed(self):
        self.path.write_text('{}')
        with self.assertRaisesRegex(Stop,'changed'):self.call()
        self.fetch.assert_not_called()
    def test_symlink(self):
        self.path.unlink();self.path.symlink_to(self.root/'outside.json');(self.root/'outside.json').write_text('{}')
        with self.assertRaisesRegex(Stop,'symlink'):self.call()
    def test_failed_editorial_validation_no_network(self):
        self.validator.side_effect=Stop('missing_evidence')
        with self.assertRaises(Stop):self.call()
        self.fetch.assert_not_called()
    def test_denied_routes_before_network(self):
        for url in ['https://x.com/anything','https://factcheck.afp.com/a','https://fullfact.org/world/video-people-collecting-iPhones-Strait-Hormuz-ai-generated/']:
            self.path.write_text(json.dumps({'sources':[{'url':url}]}))
            self.registry['candidates'][self.name]['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(Stop,'previously_denied'):self.call()
        self.fetch.assert_not_called()
    def test_http_denial_no_retry(self):
        self.fetch.side_effect=Stop('http_access_denied_403')
        with self.assertRaisesRegex(Stop,'403'):self.call()
        self.fetch.assert_called_once()
    def test_timeout_no_retry(self):
        self.fetch.side_effect=Stop('transport_timeout')
        with self.assertRaises(Stop):self.call()
        self.fetch.assert_called_once()
    def test_workflow_no_secret_or_input_interpolation_in_shell(self):
        s=Path('.github/workflows/candidate-source-check.yml').read_text()
        self.assertIn('permissions: {}',s);self.assertIn('workflow_dispatch:',s)
        for forbidden in ['secrets.', 'github.token', 'GITHUB_TOKEN', 'schedule:', '  push:', 'uses:', 'pilot.py']:
            self.assertNotIn(forbidden,s)
        self.assertEqual(s.count('${{ inputs.candidate_path }}'),1)
        self.assertIn('python3 candidate_preflight.py',s)
