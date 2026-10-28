# Scheduled publishing — prepared, NOT enabled

The first live test and independent duplicate verification succeeded. See
sources/live-test-proof.json. campaign.live_test_completed is now true.
producer_fresh_run_verified and scheduled_publication_enabled remain false.
There is no active schedule trigger. The inert template is
`deployment/scheduled-publish.yml.disabled`.

Fresh trial assessment: commit 47136b62f3e8f21d294322c4e46a18ad1411c94c
and successful CI 40645640518 prove draft-only research/storage. They do not yet
prove a fully validated ready candidate and append-only queue promotion. The draft
explicitly holds publication rights review unresolved; the source-role revision now accepts its older primary documentary evidence
without redating it. Anonymous runner preflight and full candidate promotion proof
remain pending. See `docs/producer-promotion.md`
for exact remaining acceptance checks and safe producer instructions. No schedule
or campaign readiness flag was enabled by this assessment.

Required producer proof before parent authorizes enabling:

1. An independent fresh producer run reads the current producer contract and campaign
   from the repository, including exact cutoff and allowed write paths.
2. It researches a different claim, verifies genuine source pixels/provenance and
   source dates, obtains independent automated editorial/rights review, and detects
   semantic duplicates. Empty/no-worthy-claim output is acceptable for routine work,
   but the readiness demonstration must prove valid record/render/validation handling.
3. It can write only approved public source/card/draft/queue additions; never code,
   workflow, state or configuration changes. Record run ID/time, commit, reviewer,
   evidence checks and validation results without credentials.
4. Parent confirms the observed capability and records the proof path in
   producer_readiness_record. Only then set producer_fresh_run_verified=true and
   scheduled_publication_enabled=true, and move the reviewed scheduled template to
   .github/workflows/scheduled-publish.yml. The current manual workflow can remain.

Proposed cadence: minute17 every3hours, at most one new ready card per run. No daily
volume promise. Concurrency group matches manual publishing; durable remote ownership
also fences competitors. Publisher retains live identity/quota checks, spacing,
10/day conservative cap, evidence freshness and uncertain-outcome quarantine.

Exact unchanged exclusive cutoff: 2026-11-27T06:07:35.862082+00:00. The workflow checks
window/readiness before loading publishing-step credentials, and Python checks again
around API/checkpoint latency. After cutoff it skips publication; GitHub cron itself
has no UNTIL, so disable/remove the schedule after the pilot. Public scheduling can
be delayed or skipped. Do not extend the cutoff to compensate without user authority.

Permissions: workflow default {}, publishing job Contents write and implicit Metadata
read only. No additional credential, bypass actor, runner class, cache, artifact,
package, paid service or secret scope. Instagram secret is injected only into the
publishing step; GitHub token authorizes state checkpoints only. Checkout is public
and unauthenticated. Other code in the trusted job still inherits its job permission
boundary; no untrusted PR execution is enabled.

Do not dispatch another publication merely to demonstrate duplicate prevention.
Existing independent checker used a public immutable ledger snapshot and NoAPI.
No state reset or edit is needed. Scheduled runtime will skip already-sent jobs.
