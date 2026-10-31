"""One-shot MCC reconciliation: Instagram GET-only, fixed claim and state head."""
import argparse
import copy
import datetime as dt
import json
import os
import re
import sys
from github_journal import GitHubAPI, GitHubJournal
from pilot import gate
from publisher import Instagram, Publisher, Stop, UTC, require

CLAIM = 'a1190599a5b634d1b2a63a3f37142dfdfc040aff515ff4074214420ed9e8ea53'
CONTAINER = '17897436390456374'
HEAD = 'fcf7d4387cf8644c571e344e9ef89eca66968e1f'
FINGERPRINT = '34d9c6365f1b378b28fbedb4cdd04323756111222801babec3bfbf0fffa37bcc'
ORIGINAL_ROW = [FINGERPRINT, 'publishing', '2026-10-31T13:12:53.067368+00:00', CONTAINER, None]

class ReadOnlyInstagram:
    def __init__(self, api): self.api = api
    def call(self, method, path, **params):
        require(method == 'GET' and ((path == 'me' and params == {'fields':'user_id,username'})
                or (path == CONTAINER and params == {'fields':'status_code'})), 'recovery_read_only')
        return self.api.call(method, path, **params)

class MCCJournal(GitHubJournal):
    def _load(self):
        super()._load()
        require(self.head == HEAD and self.state['owner'] is None
                and self.state['jobs'].get(CLAIM) == ORIGINAL_ROW, 'recovery_snapshot_changed')
        self.original = copy.deepcopy(self.state)
    def _checkpoint(self, updated):
        require(set(updated) == set(self.original) and updated['version'] == self.original['version']
                and set(updated['jobs']) == set(self.original['jobs']), 'recovery_scope_changed')
        for cid, row in self.original['jobs'].items():
            if cid != CLAIM: require(updated['jobs'][cid] == row, 'recovery_other_job_changed')
        row = updated['jobs'][CLAIM]
        require(row == ORIGINAL_ROW or (len(row) == 5 and row[0] == FINGERPRINT
                and row[1] == 'sent' and row[3] == CONTAINER and row[4] is None), 'recovery_target_changed')
        super()._checkpoint(updated)
    def save(self, cid, fingerprint, phase, now, container=None, media=None):
        require((cid, fingerprint, phase, container, media) ==
                (CLAIM, FINGERPRINT, 'sent', CONTAINER, None), 'recovery_scope_changed')
        super().save(cid, fingerprint, phase, now, container, media)


def run(config, env, clock=lambda:dt.datetime.now(UTC), github_factory=GitHubAPI, instagram_factory=Instagram):
    gate(config, env, clock())
    require(env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'recovery_manual_only')
    require(env.get('INSTAGRAM_ACCESS_TOKEN') and env.get('GITHUB_TOKEN'), 'missing_token')
    journal = MCCJournal(github_factory(env['GITHUB_TOKEN']), config['state_genesis'])
    api = ReadOnlyInstagram(instagram_factory(env['INSTAGRAM_ACCESS_TOKEN']))
    def bounded_clock():
        now = clock()
        gate(config, env, now)
        return now
    outcome = Publisher(journal, api, clock=bounded_clock).reconcile(CLAIM)
    head, state = journal.inspect()
    require(head == journal.head and state == journal.state and state['owner'] is None, 'recovery_unconfirmed')
    require(outcome == 'reconciled_sent' and state['jobs'][CLAIM][1] == 'sent', 'recovery_still_quarantined')
    return {'outcome':outcome, 'claim_id':CLAIM, 'container_id':CONTAINER,
            'media_id':None, 'state_head':head, 'unresolved_jobs':sum(r[1]!='sent' for r in state['jobs'].values())}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('Dry run: no credentials, network or state changes.')
        return 0
    try:
        with open('campaign.json') as f: config = json.load(f)
        print(json.dumps(run(config, os.environ), sort_keys=True))
        return 0
    except Exception as error:
        reason = str(error) if isinstance(error, Stop) and re.fullmatch('[a-z0-9_]{1,80}',str(error)) else 'unexpected_failure'
        print('STOP: '+reason+'; inspect state, never retry publication.', file=sys.stderr)
        return 1
if __name__ == '__main__': sys.exit(main())
