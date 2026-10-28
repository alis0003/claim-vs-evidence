import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

class ScheduleTemplateTests(unittest.TestCase):
    def execute_gate(self,ready=True,expired=False):
        root=Path(__file__).resolve().parents[1]
        active=root/'.github/workflows/scheduled-publish.yml'
        template=(active if active.exists() else root/'deployment/scheduled-publish.yml.disabled').read_text()
        code=textwrap.dedent(template.split("python3 - <<'PYTHON'\n")[1].split('          PYTHON')[0])
        now=dt.datetime.now(dt.timezone.utc)
        start=now-dt.timedelta(days=31 if expired else 1)
        config=dict(active=True,live_test_completed=True,producer_fresh_run_verified=ready,
                    scheduled_publication_enabled=ready,activation_at=start.isoformat(),
                    end_at=(start+dt.timedelta(days=30)).isoformat())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'campaign.json').write_text(json.dumps(config))
            env=dict(os.environ,GITHUB_OUTPUT=str(root/'output'),PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            result=subprocess.run([sys.executable,'-c',code],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return (root/'output').read_text()
    def test_eligible_gate_output_is_real_newline(self):self.assertEqual(self.execute_gate(),'allowed=true\n')
    def test_no_producer_readiness_skips_credentials(self):self.assertEqual(self.execute_gate(False),'allowed=false\n')
    def test_expired_campaign_skips_credentials(self):self.assertEqual(self.execute_gate(True,True),'allowed=false\n')
