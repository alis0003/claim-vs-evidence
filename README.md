# Claim vs Evidence — English Instagram fact checks

Authorized account: **@claimvsevidence**. Public repository:
**alis0003/claim-vs-evidence**. This repository contains the deployed publisher,
reviewed public assets, evidence records and append-only queue.

The first authorized Hormuz/Bangladesh card was published at
https://www.instagram.com/p/DfBw8BMFS16/ . Its durable sent record and independent
zero-API duplicate check are documented in sources/live-test-proof.json.
The new polar-bear card, using an original clearly labelled AI illustration,
passed independent review, hosted anonymous preflight and append-only promotion.
Its queue entry is ready; this documentation does not assert it has been published.
See sources/producer-readiness-proof.json for exact commits and CI runs.

## Scheduled publisher

.github/workflows/scheduled-publish.yml uses cron `17 */3 * * *`: minute17 every
three hours UTC. It publishes at most one due reviewed card per run. Empty ready
queues produce no posts. GitHub scheduling may be delayed or skipped; no 100%
availability or daily volume is promised.

campaign.json is canonical. Activation is 2026-10-28T06:07:35.862082+00:00 and the
exclusive end is 2026-11-27T06:07:35.862082+00:00, exactly30days later.
The scheduled workflow checks readiness and this window before injecting posting
credentials; Python checks the window again around API/checkpoint latency. After
expiry publication stops. GitHub cron has no UNTIL; disable/remove the trigger
after expiry to stop empty runner invocations. Do not extend the pilot implicitly.

live_test_completed, producer_fresh_run_verified and scheduled_publication_enabled
are true after the documented proof. The manual workflow remains guarded by its
explicit confirmation and PUBLISHING_ENABLED variable. No manual rerun is needed
to prove deduplication.

## Native research producer

The parent owns the separate native daily research task and must apply
[its current instructions](docs/native-producer-task.md). Repository deployment
cannot update that task. Research runs in flexible mornings Asia/Kolkata and may
produce zero ready candidates. Never assume every claim is false or invent claims,
sources, dates or reach to meet a target.

Read docs/producer-contract.md before every producer run. Only drafts/**, cards/**,
sources/** and append-only queue additions are permitted producer writes. A distinct
automated reviewer checks evidence, semantic duplicates, provenance and exact final
JPEG/caption bytes. No human review is implied. Unsupported or high-impact
allegations about identifiable people are held.

Three visual types are supported: rights-established claim screenshots, properly
labelled rights-cleared photos, and user-approved original AI illustrations labelled
**AI illustration — not actual footage**. Illustrations never establish the facts
or recreate an alleged real event as footage. Denied images and the blocked
HTML2Shell candidate are not reused. Full schemas and intentional non-ready samples
are queue.sample.json, candidate-photo.sample.json and candidate-ai.sample.json.

## Validation

Publishing and tests use Python standard library plus Git; producer rendering uses
Pillow. Output is baseline sRGB JPEG, normally1080x1350 and below8MB. Use:

```sh
python3 -m unittest discover -s tests -q
python3 publisher.py queue.json
python3 pilot.py --config campaign.json --queue queue.json
python3 validate_candidate.py candidate.json
```

These commands do not publish. Add `--anonymous-preflight` only to
validate_candidate.py to check public source/provenance/media availability without
Instagram credentials. HTTP success is not proof of truth or reuse rights.

Claims/circulation remain recent, checks/reviews expire after7days, jobs expire
within30days and run windows last at most24hours. Authentic older primary documents
are allowed only with timely independent fact-check evidence; dates are preserved.
Date-only and unknown capture/generation times are explicitly distinguished from
precise timestamps. See the executable schema and producer contract.

Queue-history checks retain all IDs and sent entries. Expired/future jobs receive
identity/window checks; due jobs receive current evidence validation. Legacy sent
records remain readable for deduplication, but cannot authorize new publication
without the current visual-provenance gates. Use validate_candidate.py for new jobs.

## Durable state, permissions and limits

Publishing-state stores remote checkpoints for ownership, creation intent,
container ID, publish intent and terminal media ID. Checkpoints use optimistic
heads and non-force updates; ephemeral SQLite is never the hosted durability layer.
Active branch rules block deletion and force pushes with no bypass actors.
No reset, blind POST retry or automatic recovery follows an uncertain outcome.
Explicit reconciliation is required; see DURABILITY.md.

The official Instagram Login API verifies current username/ID and quota. Limits
are conservative:10 per rolling day, minimum60minute spacing and one new card/run.
Manual and scheduled workflows share concurrency controls and durable ownership.
Sent Hormuz is preserved and will not be posted again.

INSTAGRAM_ACCESS_TOKEN is stored only in GitHub Actions Secrets and enters only
the publishing step. The automatic GITHUB_TOKEN has job-scoped Contents write for
state checkpoints. Workflow defaults grant no permissions; checkout is public and
unauthenticated. No tokens in files, chat, logs, artifacts or Git URLs.

Only free standard ubuntu-24.04 public runners are used. No paid services, external
AI APIs, larger runners, caches, uploaded artifacts or third-party Actions are used.
Existing unrelated repositories, sites and servers are outside this project's scope.

## API provenance

Parent-verified official documentation specifies graph.instagram.com/v26.0,
instagram_business_basic and instagram_business_content_publish, publicly fetchable
JPEG image_url, media container creation then media_publish. The first authorized
live test verified actual API compatibility and durable publication. Official docs:
https://developers.facebook.com/docs/instagram-platform/content-publishing/
and https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started/.
Earlier denied executor documentation retrieval was not bypassed.
