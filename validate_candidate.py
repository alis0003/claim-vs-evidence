"""Validate ONE prospective job; unlike queue history checks, enforce current rights gates."""
import argparse
import datetime as dt
import json
from pathlib import Path
from publisher import Stop, UTC, validate_ready, preflight

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--anonymous-preflight',action='store_true')
    args=parser.parse_args()
    try:
        job=json.loads(args.candidate.read_text())
        validate_ready(job,dt.datetime.now(UTC))
        if args.anonymous_preflight:preflight(job)
        print('Candidate validated'+('; anonymous source/media/rights checks passed' if args.anonymous_preflight else '; offline only'))
    except Stop as error:
        raise SystemExit('STOP: '+str(error)) from None
