"""Bounded pilot runner. Dry run by default; deployment gates fail closed."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
from github_journal import GitHubAPI, GitHubJournal, REPOSITORY
from publisher import Publisher, Instagram, Stop, UTC, require, timestamp, validate, numeric, select_due


def gate(config,env,now):
    require(config.get('repository')==REPOSITORY and config.get('username')=='claimvsevidence','wrong_deployment_target')
    for flag in ('active','parent_confirmed_secret_ready','initial_queue_reviewed'):
        require(config.get(flag) is True,'live_not_authorized')
    start,end=timestamp(config.get('activation_at')),timestamp(config.get('end_at'))
    require(start <= now < end and end-start==dt.timedelta(days=30),'pilot_outside_window')
    require(env.get('GITHUB_ACTIONS')=='true' and env.get('GITHUB_REPOSITORY')==REPOSITORY
            and env.get('GITHUB_REF')=='refs/heads/main','untrusted_runner')
    require(env.get('GITHUB_EVENT_NAME') in {'workflow_dispatch','schedule'},'untrusted_event')
    require(bool(re.fullmatch('[a-f0-9]{40}',env.get('GITHUB_SHA',''))),'untrusted_commit')
    require(env.get('PUBLISHING_ENABLED')=='true','deployment_disabled')
    if env['GITHUB_EVENT_NAME']=='schedule':
        require(config.get('live_test_completed') is True,'live_test_required')
        require(config.get('producer_fresh_run_verified') is True,'producer_readiness_required')
        require(config.get('scheduled_publication_enabled') is True,'schedule_not_authorized')
    require(bool(re.fullmatch('[a-f0-9]{40}',str(config.get('state_genesis','')))),'missing_state_genesis')
    return end


def published_receipt(api,journal,cid):
    row=journal.row(cid)
    require(row is not None and row[1]=='sent','publication_not_durably_sent')
    media=numeric(row[4])
    # A failed GET does not undo sent state and must never trigger re-publication.
    result=api.call('GET',media,fields='id,permalink')
    require(result.get('id')==media,'published_media_mismatch')
    link=result.get('permalink')
    require(isinstance(link,str),'published_permalink_unverified')
    url=urllib.parse.urlsplit(link)
    require(url.scheme=='https' and url.netloc in {'www.instagram.com','instagram.com'}
            and not url.query and not url.fragment
            and bool(re.fullmatch(r'/(p|reel)/[A-Za-z0-9_-]+/?',url.path)), 'published_permalink_unverified')
    return {'outcome':'sent','claim_id':cid,'container_id':row[3],'media_id':media,'permalink':link}


def run(config,jobs,live=False,env=None,clock=lambda:dt.datetime.now(UTC),github_factory=GitHubAPI,instagram_factory=Instagram):
    due=select_due(jobs,clock())
    if not live:return 'dry_run_no_network'
    env=os.environ if env is None else env
    end=gate(config,env,clock())
    if not due:return 'no_due_jobs'
    require(env.get('INSTAGRAM_ACCESS_TOKEN') and env.get('GITHUB_TOKEN'),'missing_token')
    journal=GitHubJournal(github_factory(env['GITHUB_TOKEN']),config['state_genesis'])
    api=instagram_factory(env['INSTAGRAM_ACCESS_TOKEN'])
    def bounded_clock():
        current=clock()
        # Called by Publisher before and after durable intent checkpoints.
        require(timestamp(config['activation_at'])<=current<end,'pilot_outside_window')
        return current
    publisher=Publisher(journal,api,clock=bounded_clock,readiness_checks=5)
    # One new card per run; never pad an empty queue. Skip already-sent records.
    for job in due:
        result=publisher.run(job,live=True)
        if result=='sent':
            try:
                print(json.dumps(published_receipt(api,journal,job['claim_id']),sort_keys=True))
            except Exception:
                raise Stop('sent_but_permalink_unverified_no_republish') from None
        if result!='already_sent':return result
    return 'already_sent'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('campaign.json'))
    parser.add_argument('--queue',type=Path,default=Path('queue.json'))
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    try:
        result=run(json.loads(args.config.read_text()),json.loads(args.queue.read_text()),args.live)
        print(result)
        return 0
    except Exception as error:
        reason=str(error) if isinstance(error,Stop) and re.fullmatch('[a-z0-9_]{1,80}',str(error)) else 'unexpected_failure'
        print('STOP: '+reason+'; inspect durable state before any retry.',file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
