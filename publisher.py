"""Conservative Instagram Login publishing core. Standard library only.
CLI deliberately offline; live deployment is not authorized or enabled.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import ssl
import struct
import sys
import time
import urllib.parse

API_ROOT = 'https://graph.instagram.com/v26.0'
USERNAME = 'claimvsevidence'
VERDICTS = {'true', 'false', 'misleading', 'out_of_context', 'unverified'}
UTC = dt.timezone.utc

class Stop(Exception):
    """Only fixed, non-secret reason codes may cross the CLI boundary."""


def require(ok, code):
    if not ok:
        raise Stop(code)


def timestamp(value):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(result.tzinfo is not None, 'invalid_timestamp')
        return result.astimezone(UTC)
    except (ValueError, TypeError, AttributeError):
        raise Stop('invalid_timestamp') from None


def recent(value, now, days):
    age = now - timestamp(value)
    require(dt.timedelta(0) <= age <= dt.timedelta(days=days), 'stale_or_future_evidence')


def public_url(url, allow_source_query=False):
    try:
        require(isinstance(url,str) and len(url)<=4096 and not re.search(r'[\x00-\x20\x7f\\]',url), 'unsafe_url')
        p = urllib.parse.urlsplit(url)
        require(p.scheme == 'https' and p.hostname and not p.username and not p.password
                and p.port in (None, 443) and not p.fragment,
                'unsafe_url')
        if p.query:
            require(allow_source_query, 'unsafe_url')
            # Public document selectors only; no auth, signatures, redirects or
            # nested URLs. Preserve original query bytes instead of stripping.
            pairs=urllib.parse.parse_qsl(p.query,keep_blank_values=True,strict_parsing=True,max_num_fields=8)
            allowed={'type','view','format','page','id','article','lang','date','q'}
            require(pairs and len({k for k,v in pairs})==len(pairs), 'unsafe_source_query')
            for key,value in pairs:
                require(key in allowed and 0<len(value)<=256
                        and bool(re.fullmatch(r'[\w .,:-]+',value)), 'unsafe_source_query')
        host = p.hostname.lower()
        require('.' in host and not host.endswith(('.local', '.localhost', '.internal', '.test', '.invalid'))
                and host not in {'localhost', 'example.com', 'example.org', 'example.net'}, 'unsafe_url')
        try:
            require(ipaddress.ip_address(host).is_global, 'unsafe_url')
        except ValueError:
            pass
        return p
    except (ValueError, TypeError, AttributeError):
        raise Stop('unsafe_url') from None


def claim_id(claim):
    return hashlib.sha256(' '.join(claim.casefold().split()).encode()).hexdigest()


def text_field(obj, key, max_length=2000):
    require(isinstance(obj.get(key), str) and 0 < len(obj[key].strip()) <= max_length,
            'missing_evidence')


def source_publication_day(source):
    """Preserve date-only precision; never invent a publication clock time."""
    if source.get('published_date') is not None:
        require(source.get('published_at') is None, 'ambiguous_source_date')
        value = source['published_date']
        require(isinstance(value, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)),
                'invalid_source_date')
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            raise Stop('invalid_source_date') from None
    return timestamp(source.get('published_at')).date()


def validate_sources(sources, now):
    require(isinstance(sources, list) and 1 <= len(sources) <= 10, 'missing_evidence')
    documentary = False
    recent_fact_check = False
    recent_count = 0
    urls = set()
    for source in sources:
        require(isinstance(source, dict), 'missing_evidence')
        for key in ('title', 'publisher', 'supports'):
            text_field(source, key)
        public_url(source.get('url'), allow_source_query=True)
        require(source['url'] not in urls, 'duplicate_source')
        urls.add(source['url'])
        recent(source.get('checked_at'), now, 7)
        day = source_publication_day(source)
        checked = timestamp(source['checked_at'])
        require(day <= checked.date(), 'source_checked_before_publication')
        if source.get('published_at') is not None:
            require(timestamp(source['published_at']) <= checked, 'source_checked_before_publication')
        require(source.get('supports_claim_analysis') is True, 'missing_evidence')
        role = source.get('evidence_role', 'recent_reporting')
        require(role in {'recent_reporting', 'recent_fact_check', 'primary_documentary'},
                'invalid_source_role')
        if role == 'primary_documentary':
            documentary = True
            require(source.get('primary_source') is True and source.get('publication_date_verified') is True,
                    'unverified_documentary_source')
            for key in ('documentary_relevance', 'publication_date_basis'):
                text_field(source, key)
        else:
            # Existing timestamp records retain their exact 30-day bound.
            if source.get('published_at') is not None:
                recent(source['published_at'], now, 30)
            else:
                require(0 <= (now.date()-day).days <= 30, 'stale_or_future_evidence')
            recent_count += 1
            if role == 'recent_fact_check':
                require(source.get('independent_fact_check') is True, 'missing_independent_fact_check')
                recent_fact_check = True
    require(recent_count > 0, 'missing_recent_evidence')
    require(not documentary or recent_fact_check, 'documentary_requires_recent_fact_check')


def validate_visual(job, now):
    """Publication gate for both licensed screenshots and licensed photographs.
    Metadata is an auditable attestation, not automatic proof of ownership.
    """
    v = job.get('visual_provenance')
    require(isinstance(v, dict), 'licensed_visual_required')
    kind = v.get('kind')
    require(kind in {'claim_screenshot', 'evidence_photo'}, 'invalid_visual_kind')
    for key in ('source_url', 'license_url', 'rights_evidence_url'):
        public_url(v.get(key), allow_source_query=True)
    for key in ('creator', 'attribution', 'license_exact', 'rights_basis', 'transformations', 'context'):
        text_field(v, key)
    require(v.get('reuse_rights_verified') is True
            and v.get('social_publication_permitted') is True
            and v.get('adaptation_permitted') is True, 'unverified_visual_rights')
    require(v.get('license_exact') in {'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0',
                                     'public-domain', 'explicit-permission'}, 'unsupported_visual_license')
    recent(v.get('rights_checked_at'), now, 7)
    require(bool(re.fullmatch('[a-f0-9]{64}', str(v.get('asset_sha256', '')))), 'missing_visual_hash')
    require(v['attribution'] in job['caption'], 'missing_visual_attribution')
    label = v.get('display_label')
    allowed = {'claim_screenshot': {'Claim screenshot'},
               'evidence_photo': {'Illustrative photo', 'Evidence photo'}}
    require(label in allowed[kind] and label in job['caption'], 'misleading_visual_label')
    review = v.get('visual_review')
    require(isinstance(review, dict) and review.get('label_visible') is True
            and review.get('context_verified') is True, 'missing_visual_review')
    require(review.get('reviewer_id') == job['reviewer']
            and review.get('jpeg_sha256') == job['image']['sha256']
            and review.get('caption_sha256') == hashlib.sha256(job['caption'].encode()).hexdigest(),
            'unbound_visual_review')
    recent(review.get('reviewed_at'), now, 7)
    text_field(review, 'notes')
    if kind == 'claim_screenshot':
        capture = job.get('screenshot_provenance', {})
        require(v.get('asset_sha256') == capture.get('sha256')
                and v.get('source_url') == capture.get('original_url'), 'unbound_screenshot')
    else:
        require(job.get('screenshot_provenance') is None, 'photo_mislabeled_as_screenshot')
        require(v.get('claim_presented_as_text') is True, 'missing_text_claim')
        recent(v.get('acquired_at'), now, 30)
        if v.get('photo_captured_at') is None:
            text_field(v, 'capture_date_note')
        else:
            require(timestamp(v['photo_captured_at']) <= now, 'future_photo_capture')
        if label == 'Evidence photo':
            text_field(v, 'evidentiary_connection')
            require(v.get('evidence_source_url') in [s['url'] for s in job['sources']],
                    'unbound_photo_evidence')
    if v['license_exact'] == 'CC-BY-SA-4.0':
        require(v.get('output_license') == 'CC-BY-SA-4.0'
                and 'CC-BY-SA-4.0' in job['caption'], 'missing_sharealike_terms')


def validate_ready(job, now):
    cid = validate(job, now)
    validate_visual(job, now)
    return cid


def validate(job, now):
    require(isinstance(job, dict), 'invalid_job')
    for key in ('claim', 'caption', 'reviewer', 'evidence_summary'):
        text_field(job, key, 2200 if key == 'caption' else 2000)
    require(job.get('claim_id') == claim_id(job['claim']), 'invalid_claim_id')
    review=job.get('review_provenance')
    require(isinstance(review,dict) and review.get('mode')=='independent_automated', 'missing_independent_review')
    for key in ('producer_id','reviewer_id','review_notes'):
        text_field(review,key)
    require(review['producer_id']!=review['reviewer_id'] and job['reviewer']==review['reviewer_id'], 'missing_independent_review')
    require(job.get('ready_for_publish') is True and job.get('editorial_verified') is True and job.get('evidence_supported') is True,
            'unverified_editorial')
    require(job.get('high_impact_identifiable_person') is False, 'high_impact_allegation')
    require(job.get('verdict') in VERDICTS and job.get('language') == 'en', 'invalid_verdict_or_language')
    if job.get('claim_date') is None:
        # Unknown post dates must not be replaced with a different video's date.
        require(job.get('claim_date_basis')=='dated_fact_check_documents_circulation', 'missing_claim_date_basis')
        text_field(job,'claim_date_note')
        observed=job.get('circulation_observed_date')
        require(isinstance(observed,str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',observed)), 'invalid_circulation_date')
        try:observed_day=dt.date.fromisoformat(observed)
        except ValueError:raise Stop('invalid_circulation_date') from None
        require(0<=(now.date()-observed_day).days<=30,'stale_or_future_evidence')
        sources=job.get('sources')
        require(isinstance(sources,list),'missing_evidence')
        matches=[s for s in sources if isinstance(s,dict) and s.get('url')==job.get('circulation_evidence_url')]
        require(len(matches)==1 and source_publication_day(matches[0])==observed_day
                and matches[0].get('evidence_role', 'recent_reporting') != 'primary_documentary'
                and matches[0].get('supports_claim_analysis') is True,'unbound_circulation_evidence')
    else:
        recent(job.get('claim_date'), now, 30)
    recent(job.get('reviewed_at'), now, 7)
    created = timestamp(job.get('created_at'))
    expires = timestamp(job.get('expires_at'))
    require(created <= now < expires <= created + dt.timedelta(days=30), 'expired_job')
    start, end = timestamp(job.get('run_after')), timestamp(job.get('run_before'))
    require(created <= start <= now < end <= expires and end-start <= dt.timedelta(hours=24),
            'expired_run_window')
    validate_sources(job.get('sources'), now)
    if job.get('visual_provenance', {}).get('kind') != 'evidence_photo':
        p = job.get('screenshot_provenance')
        require(isinstance(p, dict) and p.get('original') is True and p.get('rights_reviewed') is True,
                'missing_provenance')
        for key in ('publisher', 'context'):
            text_field(p, key)
        public_url(p.get('original_url'), allow_source_query=True)
        if p.get('captured_at') is None:
            # Filesystem save time is NOT a capture event. Preserve that distinction.
            text_field(p,'timestamp_note')
            require(p.get('timestamp_basis')=='filesystem_save_exact_capture_unrecorded', 'missing_provenance_time_basis')
            recent(p.get('saved_at_utc'),now,30)
        else:
            recent(p.get('captured_at'), now, 30)
        require(bool(re.fullmatch('[a-f0-9]{64}', str(p.get('sha256', '')))), 'missing_provenance')
    image = job.get('image')
    require(isinstance(image, dict) and image.get('mime') == 'image/jpeg', 'unsupported_media')
    public_url(image.get('url'))
    w, h = image.get('width'), image.get('height')
    require(type(w) is int and type(h) is int and 320 <= w <= 1440 and h > 0 and .8 <= w/h <= 1.91,
            'unsupported_dimensions')
    require(bool(re.fullmatch('[a-f0-9]{64}', str(image.get('sha256', '')))), 'unsupported_media')
    if 'visual_provenance' in job:
        validate_visual(job, now)
    return job['claim_id']


def select_due(jobs,now):
    """Validate identity/windows across append-only history; fully validate due jobs.
    Never discard historical IDs or consult/reset the sent ledger.
    """
    require(isinstance(jobs,list) and len(jobs)<=100,'invalid_queue')
    seen=set();due=[]
    for job in jobs:
        require(isinstance(job,dict),'invalid_job')
        text_field(job,'claim')
        cid=job.get('claim_id')
        require(cid==claim_id(job['claim']),'invalid_claim_id')
        require(cid not in seen,'duplicate_claim');seen.add(cid)
        created=timestamp(job.get('created_at'));expires=timestamp(job.get('expires_at'))
        start=timestamp(job.get('run_after'));end=timestamp(job.get('run_before'))
        require(created<=start<end<=expires<=created+dt.timedelta(days=30)
                and end-start<=dt.timedelta(hours=24),'invalid_queue_window')
        if not start<=now<end:continue
        validate(job,now);due.append(job)
    return due


class PinnedHTTPS(http.client.HTTPSConnection):
    """DNS checked once; socket pinned to that public IP; TLS verifies original host."""
    def connect(self):
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        require(addresses and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses), 'unsafe_dns')
        raw = socket.create_connection((addresses[0][4][0], 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def request(url, method='GET', data=None, token=None, limit=8_000_000, source=False):
    """No redirects, proxies, retries, cookies, response logging or exception echo."""
    conn = None
    try:
        p = urllib.parse.urlsplit(url)
        if token is not None:
            require(p.scheme == 'https' and p.netloc == 'graph.instagram.com', 'unsafe_api_host')
        else:
            public_url(url, allow_source_query=source)
        conn = PinnedHTTPS(p.hostname, timeout=20, context=ssl.create_default_context())
        headers = {'Accept': '*/*'}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        conn.request(method, urllib.parse.urlunsplit(('', '', p.path or '/', p.query, '')), body, headers)
        r = conn.getresponse()
        if r.status != 200:
            # Numeric HTTP status only. Never log response bodies or headers.
            if r.status in (401,403):reason='http_denied_'
            elif r.status==407:reason='http_proxy_auth_'
            elif r.status==429:reason='http_rate_limited_'
            elif 300<=r.status<400:reason='http_redirect_'
            else:reason='http_status_'
            raise Stop(reason+str(r.status))
        payload = r.read(limit+1)
        require(len(payload) <= limit and payload, 'invalid_response_size')
        return r.getheader('Content-Type', '').split(';')[0].lower(), payload
    except Stop:
        raise
    except socket.gaierror:
        raise Stop('dns_failure') from None
    except TimeoutError:
        raise Stop('transport_timeout') from None
    except ssl.SSLError:
        raise Stop('tls_failure') from None
    except PermissionError:
        raise Stop('network_permission_denied') from None
    except ConnectionRefusedError:
        raise Stop('connection_refused') from None
    except ConnectionResetError:
        raise Stop('connection_reset') from None
    except OSError:
        raise Stop('network_transport_failure') from None
    except Exception:
        raise Stop('transport_failure') from None
    finally:
        if conn:
            conn.close()


class Instagram:
    def __init__(self, token):
        require(isinstance(token, str) and token.strip() and '\n' not in token and '\r' not in token, 'missing_token')
        self._token = token

    def call(self, method, path, **fields):
        require(bool(re.fullmatch(r'(me|[0-9]+)(/(media|media_publish|content_publishing_limit))?', path)), 'invalid_api_path')
        url = API_ROOT + '/' + path
        if method == 'GET':
            url += '?' + urllib.parse.urlencode(fields)
        try:
            mime, raw = request(url, method, fields if method == 'POST' else None, self._token, 1_000_000)
            result = json.loads(raw)
            require(isinstance(result, dict) and 'error' not in result, 'api_failure')
            return result
        except Stop:
            raise
        except Exception:
            raise Stop('invalid_api_response') from None


def jpeg_dimensions(data):
    require(data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'), 'unsupported_media')
    i = 2
    dims = None
    try:
        while i < len(data)-2:
            require(data[i] == 255, 'unsupported_media')
            while data[i] == 255:
                i += 1
            marker = data[i]; i += 1
            if marker == 0xDA:
                break
            length = struct.unpack('>H', data[i:i+2])[0]
            require(length >= 2 and i+length <= len(data), 'unsupported_media')
            # Only simple baseline RGB/grayscale JPEG; reject progressive, MPO/JPS.
            require(marker not in {0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}
                    and b'MPF\x00' not in data[i:i+length] and b'_JPSJPS_' not in data[i:i+length], 'unsupported_media')
            if marker == 0xC0:
                require(length >= 11 and data[i+2] == 8 and data[i+7] in (1,3), 'unsupported_media')
                h,w = struct.unpack('>HH', data[i+3:i+7]); dims=(w,h)
            i += length
        require(dims is not None and marker == 0xDA, 'unsupported_media')
        return dims
    except (IndexError, struct.error, UnboundLocalError):
        raise Stop('unsupported_media') from None


def preflight(job, fetch=request, now=None):
    # This check is also used before resuming a known created container.
    validate_visual(job, now if now is not None else dt.datetime.now(UTC))
    visual = job['visual_provenance']
    for url in dict.fromkeys(visual[key] for key in ('source_url', 'license_url', 'rights_evidence_url')):
        mime, raw = fetch(url, limit=2_000_000, source=True)
        require(mime in {'text/html', 'text/plain', 'application/pdf'} and len(raw.strip()) >= 40, 'unreadable_rights_metadata')
    for s in job['sources']:
        mime, raw = fetch(s['url'], limit=2_000_000, source=True)
        require(mime in {'text/html','text/plain','application/pdf'} and len(raw.strip()) >= 40, 'unreadable_source')
    mime, data = fetch(job['image']['url'])
    require(mime == 'image/jpeg' and hashlib.sha256(data).hexdigest() == job['image']['sha256'], 'media_mismatch')
    require(jpeg_dimensions(data) == (job['image']['width'],job['image']['height']), 'media_mismatch')


class Journal:
    """Caller must retain this database across runs; never delete it to retry."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=0)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (claim_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, phase TEXT NOT NULL, at TEXT NOT NULL, container TEXT, media TEXT)')
        self.db.commit()

    @contextlib.contextmanager
    def exclusive(self):
        # Separate process lock survives commits and covers all network operations.
        import fcntl
        row = self.db.execute('PRAGMA database_list').fetchone()
        require(bool(row[2]), 'durable_state_required')
        with open(row[2]+'.lock', 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Stop('concurrent_run') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def row(self, cid):
        return self.db.execute('SELECT fingerprint,phase,at,container,media FROM jobs WHERE claim_id=?',(cid,)).fetchone()

    def save(self, cid, fingerprint, phase, now, container=None, media=None):
        self.db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?)',
                        (cid,fingerprint,phase,now.isoformat(),container,media))
        self.db.commit()

    def times(self, exclude=None):
        return [r[0] for r in self.db.execute('SELECT at FROM jobs WHERE claim_id != ?', (exclude or '',))]

    def unresolved(self, exclude=None):
        return bool(self.db.execute("SELECT 1 FROM jobs WHERE phase != 'sent' AND claim_id != ?", (exclude or '',)).fetchone())


def numeric(value):
    require(isinstance(value,str) and bool(re.fullmatch('[0-9]+', value)), 'invalid_api_id')
    return value


class Publisher:
    def __init__(self, journal, api, fetch=request, clock=lambda:dt.datetime.now(UTC), readiness_checks=1, sleeper=time.sleep):
        self.journal, self.api, self.fetch, self.clock = journal,api,fetch,clock
        require(type(readiness_checks) is int and 1<=readiness_checks<=5,'invalid_readiness_checks')
        self.readiness_checks,self.sleeper=readiness_checks,sleeper

    def identity(self):
        me = self.api.call('GET','me',fields='user_id,username')
        require(me.get('username') == USERNAME, 'wrong_identity')
        return numeric(me.get('user_id'))

    def quota(self, account, now, exclude=None):
        try:
            q=self.api.call('GET',account+'/content_publishing_limit',fields='quota_usage,config')['data'][0]
            usage,total,duration=q['quota_usage'],q['config']['quota_total'],q['config']['quota_duration']
            require(all(type(x) is int for x in (usage,total,duration)) and usage>=0 and total>0 and duration==86400, 'unreadable_quota')
            require(usage < min(total,10), 'quota_exhausted')
        except (KeyError,IndexError,TypeError):
            raise Stop('unreadable_quota') from None
        times=[timestamp(t) for t in self.journal.times(exclude)]
        require(not any(t>now for t in times), 'state_clock_error')
        require(sum(t>now-dt.timedelta(days=1) for t in times)<10, 'rolling_limit')
        require(not any(t>now-dt.timedelta(minutes=60) for t in times), 'spacing_limit')

    def run(self, job, live=False):
        cid=validate(job,self.clock())
        fp=hashlib.sha256(json.dumps(job,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if not live:
            return 'dry_run_validated_no_network'
        with self.journal.exclusive():
            previous=self.journal.row(cid)
            if previous:
                require(previous[0]==fp, 'changed_job')
                return 'already_sent' if previous[1]=='sent' else 'reconciliation_required'
            # Legacy records may be read/deduplicated, never newly published.
            validate_visual(job, self.clock())
            require(self.api is not None, 'missing_token')
            account=self.identity()
            # Uncertain work blocks all new publication, not just this claim.
            require(not self.journal.unresolved(), 'reconciliation_required')
            self.quota(account,self.clock())
            preflight(job,self.fetch,self.clock())
            validate(job,self.clock())
            # Durable intent BEFORE every POST: even a crash cannot authorize replay.
            self.journal.save(cid,fp,'creating',self.clock())
            validate(job,self.clock())
            try:
                container=numeric(self.api.call('POST',account+'/media',image_url=job['image']['url'],caption=job['caption']).get('id'))
            except Exception:
                raise Stop('creation_uncertain_reconcile') from None
            self.journal.save(cid,fp,'created',self.clock(),container)
            return self._publish(job,cid,fp,account,container)

    def _publish(self,job,cid,fp,account,container):
        for attempt in range(self.readiness_checks):
            validate(job,self.clock())
            status=self.api.call('GET',container,fields='status_code').get('status_code')
            if status=='FINISHED':break
            require(status=='IN_PROGRESS','container_not_ready_reconcile')
            if attempt+1<self.readiness_checks:self.sleeper(60)
        require(status=='FINISHED', 'container_not_ready_reconcile')
        validate(job,self.clock())
        # Fresh remote quota after processing; local reservation already counted.
        q=self.api.call('GET',account+'/content_publishing_limit',fields='quota_usage,config')
        try:
            r=q['data'][0]; u=r['quota_usage']; t=r['config']['quota_total']; d=r['config']['quota_duration']
            require(type(u) is int and type(t) is int and type(d) is int and d==86400 and 0<=u<min(t,10), 'quota_exhausted')
        except (KeyError,IndexError,TypeError):
            raise Stop('unreadable_quota') from None
        validate(job,self.clock())
        self.journal.save(cid,fp,'publishing',self.clock(),container)
        validate(job,self.clock())
        try:
            media=numeric(self.api.call('POST',account+'/media_publish',creation_id=container).get('id'))
        except Exception:
            raise Stop('publication_uncertain_reconcile') from None
        self.journal.save(cid,fp,'sent',self.clock(),container,media)
        return 'sent'

    def resume_created(self, job):
        """Only a durably recorded container with NO publish attempt may resume.
        A publishing/creating intent is quarantined, regardless of remote status.
        """
        cid=validate(job,self.clock())
        fp=hashlib.sha256(json.dumps(job,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.journal.exclusive():
            account=self.identity()
            row=self.journal.row(cid)
            require(row is not None and row[0]==fp and row[1]=='created', 'unsafe_resume')
            require(not self.journal.unresolved(cid), 'reconciliation_required')
            require(self.clock()-timestamp(row[2]) < dt.timedelta(hours=23), 'container_too_old')
            self.quota(account,self.clock(),exclude=cid)
            preflight(job,self.fetch,self.clock())
            return self._publish(job,cid,fp,account,numeric(row[3]))

    def reconcile(self,cid):
        """Read-only API reconciliation. NEVER retry a POST after uncertainty.
        PUBLISHED is terminal; every other outcome remains quarantined.
        A created-but-never-published container can be resumed separately.
        """
        with self.journal.exclusive():
            self.identity()
            row=self.journal.row(cid)
            require(row is not None, 'unknown_claim')
            fp,phase,at,container,media=row
            if phase=='sent': return 'already_sent'
            require(container is not None, 'creation_unknown_manual_review_required')
            status=self.api.call('GET',numeric(container),fields='status_code').get('status_code')
            if status=='PUBLISHED':
                self.journal.save(cid,fp,'sent',self.clock(),container,media)
                return 'reconciled_sent'
            return 'quarantined_'+ ('ready' if phase=='created' and status=='FINISHED' else 'uncertain')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('queue',type=Path)
    args=parser.parse_args()
    try:
        jobs=json.loads(args.queue.read_text())
        due=select_due(jobs,dt.datetime.now(UTC))
        print(f'DRY RUN: {len(due)} due jobs fully validated; {len(jobs)-len(due)} historical/future jobs retained with identity/window checks. No network or publishing.')
        return 0
    except Exception:
        # Do not print queue text, tracebacks, transport errors, token or headers.
        print('STOP: queue invalid or unreadable; no network or publishing.',file=sys.stderr)
        return 1

if __name__=='__main__':
    sys.exit(main())
