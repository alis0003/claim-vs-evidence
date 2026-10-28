# Producer promotion procedure

The fresh HTML2Shell trial at commit
47136b62f3e8f21d294322c4e46a18ad1411c94c proves draft production and safe holding,
not a ready-queue promotion. Its offline CI run 40645640518 passed. That CI checks
code and the operational queue; it does not attest that draft metadata is a valid
publication job. Keep this draft out of queue.json.

Remaining acceptance proof: one independently reviewed candidate must pass the
actual queue schema, final JPEG inspection, public media/source preflight and
append-only promotion. No additional Instagram publication is needed to establish
this producer capability. A missing license alone is not a legal determination;
however this draft explicitly records unresolved social-publication rights review.
Do not change that attestation without an actual scoped review. Its primary Kirby
advisory is dated April 23. The source-role revision now permits this authentic
older documentary source alongside a recently published independent fact check;
see docs/producer-contract.md. No date is changed. The revised draft source record
passes that schema, while executor anonymous requests encountered DNS failure.
A manual secret-free runner workflow, draft-preflight.yml, can test current source
and immutable draft JPEG availability without publishing. The baseline draft JPEG and a new independent review bound to its exact hash and
caption are recorded in drafts/html2shell/jpeg-review.json. It still visibly says
DRAFT NOT PUBLISHED and is not a publication-ready candidate.

## Instructions for each fresh native producer run

1. Read the current main versions of campaign.json, docs/producer-contract.md,
   queue.sample.json and publisher.py. Read queue.json and the publishing-state
   ledger for exact and semantic duplicates. Stop promotion at the exclusive
   campaign end; do not move dates, edit sent records, or change readiness flags.
2. Research a narrow supported claim and retain genuine screenshot bytes, source
   dates, provenance, hashes and truthful independent automated reviewer identity.
   Respect source denials. Save an unresolved candidate under drafts/ only. Never
   attest original-post access when the capture is a secondary reproduction.
3. Obtain independent evidence/editorial and scoped screenshot-use review of the
   final wording and final image. Preserve attribution and uncertainty. A review
   record must not claim ownership, a license or a legal guarantee without evidence.
4. Render with `python3 render_card.py approved.png cards/claim-id.jpg`; inspect
   the actual JPEG pixels and record its SHA-256 and dimensions. Commit approved
   public assets first. Use the immutable commit-addressed raw GitHub JPEG URL.
5. Build ONE candidate object using queue.sample.json and the executable validator,
   never by copying draft provenance into queue wholesale. Fill actual times when
   ready: run_after must be at or before validation now, run_before within 24 hours
   and before the campaign end, expiry within 30 days. Allow adequate time for the
   three-hour publisher cadence; GitHub scheduling can be delayed or skipped.
6. Fully validate this candidate directly using the commands below. Queue-wide
   due-aware CI may skip future or expired jobs, so its success alone is insufficient.
   Do not put a not-yet-due candidate in queue to evade full validation.
7. Append the validated object without changing any existing queue entry, using
   an optimistic expected-head update. On conflict re-read and recheck duplicates;
   never force-push. Allowed writes are only drafts/**, cards/**, sources/** and
   append-only queue.json. Confirm remote bytes, commit and offline CI success.
8. Record run identifier, actual run time, input contract commit, candidate hash,
   reviewer identity, evidence/rights review, JPEG inspection and exact validation
   results under sources/. Report zero ready candidates when checks remain open.
   Never dispatch publishing, change workflows/configuration/state/settings, use
   credentials, or contact a paid service from the producer.

## Candidate checks (no Instagram token or publication)

Use the repository Python modules in an isolated environment. candidate.json is
one job object, not an array. The second command makes normal anonymous public
requests; stop on denial rather than trying an alternate route to the same source.

```sh
python3 - <<'PY'
import datetime as dt, json
from publisher import validate_ready
candidate = json.load(open('candidate.json'))
validate_ready(candidate, dt.datetime.now(dt.timezone.utc))
print('candidate schema valid now')
PY
```

```sh
python3 - <<'PY'
import datetime as dt, json
from publisher import validate_ready, preflight
candidate = json.load(open('candidate.json'))
validate_ready(candidate, dt.datetime.now(dt.timezone.utc))
preflight(candidate)
print('anonymous source/media preflight passed')
PY
```

This is an anonymous evidence/media check, not an Instagram call.
Never infer factual verification or reuse permission from an HTTP success.
Then run `python3 publisher.py queue.json` and
`python3 -m unittest discover -s tests -q` on the proposed append-only queue.

Only after the parent verifies this fresh promotion proof may campaign flags
producer_fresh_run_verified and scheduled_publication_enabled become true, with
producer_readiness_record pointing to the proof. The existing template then moves
to .github/workflows/scheduled-publish.yml. Proposed cron is `17 */3 * * *` UTC;
exclusive cutoff remains 2026-11-27T06:07:35.862082+00:00. Do not claim it is active
until the workflow and flags are committed and checked. No daily volume guarantee.

HTML2Shell queue promotion was rejected by automatic approval review for unresolved
reuse permission. No queue commit executed. Its earlier candidate/preflight proof
does not authorize promotion under the new licensed-format contract. Do not retry
without materially new rights evidence or use the new format as an indirect bypass.
