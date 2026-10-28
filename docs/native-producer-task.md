# Native daily producer instructions

Run in flexible mornings Asia/Kolkata. Read current main campaign.json,
docs/producer-contract.md, queue.sample.json, candidate-photo.sample.json,
candidate-ai.sample.json and validate_candidate.py before work. Read queue and
publishing-state ledger for exact and semantic duplicates. Stop new promotion at
exclusive campaign end 2026-11-27T06:07:35.862082+00:00; never extend the pilot.

Research current worldwide claims; choose only supported narrow English verdicts.
Do not assume claims are false or invent viral reach. Hold unsupported claims and
high-impact allegations about identifiable people. Zero ready candidates is valid.
Read genuine evidence, retain actual publication/check dates and original-access
limitations. Attribute secondary reporting; no fabricated timestamps or sources.

Use a rights-established genuine claim screenshot, a rights-cleared illustrative
photo with truthful label, or a new user-approved original AI illustration clearly
labelled AI illustration — not actual footage. Generated art is never factual
evidence or an event reconstruction. Never retrieve/reuse denied assets or retry
the blocked HTML2Shell candidate as a workaround. Use native built-in research and
image generation, no paid services or third-party AI APIs. Follow the Library skill
for supported materialization; on unavailable bytes hold rather than fabricate.

Store exact public evidence/generation/rights provenance. Compose and inspect a
baseline sRGB1080x1350 JPEG. A distinct automated reviewer must independently check
facts, source dates, visual truthfulness, rights/provenance, exact final JPEG and
caption hashes, and semantic duplicates. Record actual reviewer identity/time;
never claim human review. Any final content change requires new review.

Allowed writes only drafts/**, cards/**, sources/** and append-only queue.json.
Commit reviewed assets/provenance first, use immutable commit-addressed URLs, then
build the candidate from the current schema. Run validate_candidate.py candidate.json
and supported anonymous preflight; preserve denials and stop that route. Run full
offline CI on the proposed queue. Use optimistic expected-head updates without force;
on conflicts re-read and recheck duplicates. Never alter existing queue entries.
Ready run windows must be current, <=24hours, inside campaign and expiry; allow time
for the three-hour publisher cadence. Do not refresh expired jobs or pad volume.

Only append when all gates pass. Record public run/proof details and verify remote
commit/CI. Report held candidates with precise reasons. Never change code, workflows,
configuration, state, secrets or settings, and never manually dispatch publication.
The scheduled publisher handles due approved jobs and durable deduplication. Do not
promise 100% availability or 50–100 daily posts.
