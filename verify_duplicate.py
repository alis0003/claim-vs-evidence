"""Independent offline duplicate guard check using a verified public state snapshot.
No credentials, API clients, or network operations are available to this checker.
"""
import argparse
import contextlib
import datetime as dt
import json
from pathlib import Path
import sys
from git_journal import GitJournal
from publisher import Publisher, Stop, UTC, require

class ReadOnlySnapshot:
    def __init__(self,state):self.state=GitJournal.decode_raw(json.dumps(state))
    @contextlib.contextmanager
    def exclusive(self):yield
    def row(self,cid):
        row=self.state['jobs'].get(cid)
        return tuple(row) if row else None
    def save(self,*args,**kwargs):raise Stop('unexpected_state_write')
    def unresolved(self,*args,**kwargs):raise Stop('unexpected_new_publication')
    def times(self,*args,**kwargs):raise Stop('unexpected_new_publication')

class NoAPI:
    def call(self,*args,**kwargs):raise Stop('unexpected_instagram_call')

def no_fetch(*args,**kwargs):raise Stop('unexpected_media_fetch')

def verify(job,state,now):
    journal=ReadOnlySnapshot(state)
    require(state['owner'] is None,'owner_still_held')
    row=journal.row(job['claim_id'])
    require(row is not None and row[1]=='sent' and row[3] and row[4],'publication_not_confirmed')
    result=Publisher(journal,NoAPI(),no_fetch,lambda:now).run(job,live=True)
    require(result=='already_sent','duplicate_guard_failed')
    return 'already_sent; zero API calls; zero state writes'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',type=Path,default=Path('queue.json'))
    parser.add_argument('--state',type=Path,required=True)
    args=parser.parse_args()
    try:
        jobs=json.loads(args.queue.read_text());require(len(jobs)==1,'single_card_test_required')
        print(verify(jobs[0],json.loads(args.state.read_text()),dt.datetime.now(UTC)))
        return 0
    except Exception:
        print('STOP: duplicate verification incomplete; inspect public state before any retry.',file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
