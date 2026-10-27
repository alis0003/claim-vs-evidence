# Claim vs Evidence — English Instagram fact checks

Target: `@claimvsevidence`. Authorized repository: `alis0003/claim-vs-evidence`.
The campaign is **inactive**, the queue is empty, and no card has been published.
Only offline CI is enabled. No purchases, paid APIs, larger runners or password bots.

## Check locally

Python 3.10+ and Git; publishing code uses the standard library. Local journal tests
use Unix locking. No credentials or network are needed for these commands:

```sh
python3 -m unittest discover -s tests -q
python3 publisher.py queue.json
python3 pilot.py --config campaign.json --queue queue.json
```

`queue.sample.json` is an intentionally rejected template. Never mistake it for a
verified fact check. Native research producers must read `docs/producer-contract.md`.
They work quality-first in flexible mornings Asia/Kolkata: zero ready posts is valid.
The software does not discover claims or verify truth; it enforces evidence metadata,
explicit editorial attestations, narrow verdicts, dates, provenance and media rules.
Never assume every viral claim is false or pad a queue to meet a volume target.

## Editorial and media gate

Ready jobs require ready_for_publish/editorial_verified/evidence_supported=true and
high_impact_identifiable_person=false. Unsupported claims and high-impact allegations
about identifiable people are held. Verdicts: true, false, misleading, out_of_context,
unverified. `unverified` still requires evidence supporting that limited conclusion.
Canonical claim IDs hash normalized wording; semantic duplicates need editorial review.

Claim/source/capture dates must be <=30 days old; review/check dates <=7 days old.
Jobs expire within 30 days and have a <=24-hour run window. Never falsify old source
dates to bypass checks. Exact JSON fields and commands are in the producer contract.

Baseline JPEG only: 320–1440 px width, aspect 0.8–1.91, <=8 MB; approved layout is
1080x1350 sRGB. `render_card.py` uses Pillow in the producer environment only. Inspect
approved input and output pixels. Header validation is not a full JPEG decoder.
The live preflight requires anonymous HTTPS media fetch, exact hash/dimensions and
readable sources; private DNS/IPs, redirects, credential URLs and query strings fail.
HTTP readability is not evidence verification. Original screenshot provenance and
rights require actual review, not a checkbox inferred from a URL.

## Durable state and limits

`git_journal.py` proves the protocol against local bare Git repositories.
`github_journal.py` implements the fixed authorized repository's REST Git transport.
It checkpoints account-wide ownership, creation intent, container ID, publish intent
and terminal media ID remotely, using expected heads and non-force ref updates.
No local ephemeral SQLite fallback is allowed for hosted publishing.

Failed or ambiguous checkpoints stop execution. Failed/timeout API POSTs remain
quarantined, never automatically retried. Reconciliation is explicit and only a
confirmed PUBLISHED status can close an uncertain publication. A known created
container with no publish attempt may resume after fresh gates; no recreation.
Read `DURABILITY.md` before configuring the protected state branch or recovery.

Identity comes from Instagram Login `/me` and must match claimvsevidence. The numeric
ID is not hardcoded. Live quota is fetched before create and publish. Conservative
limits: <=10 posts per rolling day, at least 60 minutes between attempts, one new
card per run. Any unresolved attempt blocks other new work for the account.

## Deployment gates and secrets

`campaign.json` is canonical and inactive. `activation_at` and exclusive `end_at`
must be exactly 30 elapsed days apart. Runtime checks the window again around
checkpoint latency. Secret readiness, reviewed initial queue and successful live
test are separate flags. Scheduled execution requires the successful live-test flag.

Required secret: **INSTAGRAM_ACCESS_TOKEN**. The parent browser worker owns official
Meta authorization and direct secure insertion into GitHub Actions Secrets. Never
put tokens in files, chat, command lines, logs, artifacts or Git URLs. The separate
short-lived **GITHUB_TOKEN** is supplied by Actions with Contents write permission
only in the eventual trusted publisher job. HTTP errors never echo token/header/body.

`.github/workflows/review.yml` runs offline tests and validation on standard
ubuntu-24.04, with no secret inputs, third-party Actions, cache or uploaded artifacts.
The live workflow template is inert at `deployment/publish.yml.disabled`. It cannot
run merely by adding a secret. Activate only after parent readiness confirmation,
state-branch provisioning/protection, and explicit review. Keep the schedule commented
until an authorized one-card end-to-end test succeeds. Public scheduling can be late
or skipped; the hard time window prevents publishing after pilot expiry.

## Current deployment status

Parent browser worker created and verified the public repository; initial commit
`3ce031a390641e896a915641c8fd35c926580311`. The authorized connector independently
confirmed the repository and write access. Code deployment uses expected-head checks;
this source snapshot prepares offline CI only. No existing repository is modified.
The invalid CLI credential is not reused; parent owns Instagram Secret insertion.

Initial PNG Library ID: libfile_283d3f23d1208191ac741ba5354bad1e. Library download
failed initially and on one supported retry with generic `download failed` (no
HTTP status). Parent then explicitly authorized a public GitHub asset route. That
route succeeded; PNG hash matched, PNG/JPEG pixels were inspected, and the committed
1080x1350 sRGB JPEG was anonymously fetched with matching SHA-256 (212685 bytes).
See `sources/initial-card.json` and `drafts/initial-queue.json`. Initial queue remains
held for original screenshot provenance and parent review; queue.json is empty.

Durable state branch is initialized at pinned genesis
`26d1b1261d6b904a38ce8bd9df973d6b5d07c65d`. Branch protection and parent readiness
remain prerequisites to live use. Code commit d2b7dc0126621a6d2e0d60f75b6fdd7f09610267
triggered offline CI; its outcome must be checked in Actions, not inferred from
local tests. Campaign remains inactive with no activation/end dates.

## API documentation provenance

Parent-supplied official Meta findings: Instagram Login, graph.instagram.com/v26.0,
instagram_business_basic and instagram_business_content_publish, public JPEG
image_url, create container then media_publish. Parent reports dashboard tokens
last 60 days, allowing a 30-day pilot without app-secret/refresh handling if valid.
Sources: https://developers.facebook.com/docs/instagram-platform/content-publishing/
and https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started/.
These are parent findings, not independent executor verification. Earlier executor
Meta retrieval was denied and was not retried. Actual API compatibility needs an
authorized live test. GitHub ref/auth documentation was checked read-only during
implementation; hosted API behavior is currently tested with local mocked REST.
