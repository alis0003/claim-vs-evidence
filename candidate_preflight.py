"""Manual, anonymous preflight for explicitly reviewed, hash-bound candidates."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from publisher import Stop, UTC, require, validate_ready, preflight

PATH = re.compile(r'(?:drafts|sources)/[a-z0-9][a-z0-9_/-]*\.json\Z')
# Known denied routes are excluded, including originals not independently accessible.
DENIED_HOSTS = {'x.com', 'twitter.com', 'web.archive.org', 'factcheck.afp.com',
                'images.unsplash.com', 'upload.wikimedia.org', 'www.fws.gov'}
DENIED_MARKERS = ('html2shell', 'iphone-recovery', 'video-people-collecting-iphones-strait-hormuz-ai-generated',
                  'fake-video-shows-people-fishing-iphones-out-of-water')

def check_path(root, name):
    require(isinstance(name, str) and len(name) <= 180 and bool(PATH.fullmatch(name)), 'unsafe_candidate_path')
    parts = Path(name).parts
    require(all(p not in {'.', '..'} for p in parts) and '//' not in name, 'unsafe_candidate_path')
    root = root.resolve()
    target = root / name
    require(not any((root.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts)+1)), 'symlink_candidate')
    require(target.is_file() and target.resolve().is_relative_to(root), 'missing_candidate')
    require(target.stat().st_size <= 200_000, 'candidate_too_large')
    return target

def reject_denied(value):
    if isinstance(value, dict):
        for v in value.values(): reject_denied(v)
    elif isinstance(value, list):
        for v in value: reject_denied(v)
    elif isinstance(value, str):
        lower = value.lower()
        require(not any(marker in lower for marker in DENIED_MARKERS), 'previously_denied_candidate')
        if lower.startswith(('https://', 'http://')):
            host = (urlsplit(value).hostname or '').lower()
            require(not any(host == h or host.endswith('.'+h) for h in DENIED_HOSTS), 'previously_denied_route')

def run(root, name, registry, now, validator=validate_ready, fetcher=preflight):
    path = check_path(root, name)
    entries = registry.get('candidates', {})
    require(isinstance(entries, dict) and name in entries, 'candidate_not_review_allowlisted')
    entry = entries[name]
    raw = path.read_bytes()
    require(entry.get('approved_for_anonymous_preflight') is True and bool(entry.get('review_record')), 'preflight_review_missing')
    require(entry.get('sha256') == hashlib.sha256(raw).hexdigest(), 'reviewed_candidate_changed')
    job = json.loads(raw)
    reject_denied(job)
    validator(job, now)  # Includes independent reviewer and exact visual/caption bindings.
    fetcher(job)  # Existing pinned-DNS HTTPS/SSRF checks; no retry wrapper.
    return 'Anonymous candidate preflight passed; no queue or publication changes.'

if __name__ == '__main__':
    try:
        require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'main_branch_required')
        require(os.environ.get('GITHUB_REPOSITORY') == 'alis0003/claim-vs-evidence', 'wrong_repository')
        require(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'manual_only')
        root = Path(__file__).resolve().parent
        registry = json.loads((root/'sources/preflight-reviewed-candidates.json').read_text())
        print(run(root, os.environ.get('CANDIDATE_PATH'), registry, dt.datetime.now(UTC)))
    except Exception as error:
        reason = str(error) if isinstance(error, Stop) else 'invalid_preflight_input'
        print('STOP: '+reason)
        raise SystemExit(1) from None
