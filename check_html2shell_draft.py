"""Secret-free, anonymous draft evidence/media check. Never publishes."""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from publisher import Stop, UTC, preflight, require, validate_sources


def check(commit):
    require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'invalid_asset_commit')
    directory = Path('drafts/html2shell')
    evidence = json.loads((directory / 'source-evidence.json').read_text())
    review = json.loads((directory / 'jpeg-review.json').read_text())
    now = dt.datetime.now(UTC)
    validate_sources(evidence['sources'], now)
    # This records circulation by the dated fact check, not the original post time.
    fact_check = next(s for s in evidence['sources'] if s['evidence_role'] == 'recent_fact_check')
    require(fact_check['published_date'] == '2026-10-25', 'unbound_circulation_evidence')
    image = dict(url=f'https://raw.githubusercontent.com/alis0003/claim-vs-evidence/{commit}/'
                 'drafts/html2shell/html2shell-claim-vs-evidence-DRAFT.jpg',
                 mime='image/jpeg', width=1080, height=1350, sha256=review['jpeg_sha256'])
    preflight(dict(sources=evidence['sources'], image=image))
    print('Draft source/media preflight passed; NOT queue validation or publication approval.')


if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2, 'asset_commit_required')
        check(sys.argv[1])
    except Stop as error:
        raise SystemExit('Draft preflight stopped: ' + str(error)) from None
