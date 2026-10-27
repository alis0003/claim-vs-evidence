# Native research producer contract

Read this contract, `campaign.json`, `queue.sample.json`, and `publisher.py` before
producing anything. Never invent queue fields or populate unknown evidence values.
Research runs in flexible mornings in Asia/Kolkata. Quality comes first: zero posts
is acceptable, there is no daily volume guarantee and no invented/weak debunks.
No third-party AI API, paid service, password bot or private Instagram endpoint.

## Campaign authority

`campaign.json` is the single canonical configuration. `active` is currently false.
`activation_at` must be a timezone-aware ISO timestamp and `end_at` must be EXACTLY
30 elapsed days later; end_at is exclusive. Do not activate or move these dates.
Do not modify secret-readiness, initial-review or live-test flags. Schedule triggers
are not punctuality guarantees; the runtime rejects publication outside this window.
While inactive, prepare reviewed drafts only. Do not publish or promote initial queue.

## Allowed producer writes

Only `drafts/**`, `cards/**`, `sources/**`, and append-only additions to `queue.json`
are permitted. Do not modify code, workflows, campaign configuration, state branch,
secrets, account settings, repository settings, tests or completed queue records.
Never overwrite an existing stable claim ID to evade deduplication. Human review
must also catch semantically duplicate claims with different wording. Do not write
private/unredacted screenshots, identifying sensitive data or credentials publicly.

## Editorial and ready gate

Identify the exact narrow claim, date and context. Do not assume every viral claim
is false. Supported verdicts: true, false, misleading, out_of_context, unverified.
Skip unsupported allegations and high-impact allegations about identifiable people.
Capture the actual source/screenshot, read the evidence, verify source metadata,
inspect final rendered pixels and review screenshot provenance/rights. Attribute
secondary reporting rather than claiming independent verification of originals.
A URL that loads is not proof. `unverified` requires evidence for that limited verdict.

A producer may append a ready job only when campaign is active, initial review is
complete, and EVERY validation below passes. Until then save drafts outside queue.
`ready_for_publish`, `editorial_verified`, and `evidence_supported` must all be true;
`high_impact_identifiable_person` must be explicitly false. Never set an attestation
true merely to pass a validator. Keep the queue empty if any check is unresolved.

## Queue schema

Use `queue.sample.json` as the canonical field template and `publisher.validate`
as the executable schema. Top level is a JSON array, maximum 100 jobs. Each job:

- `claim`: narrow factual claim; `claim_id`: `publisher.claim_id(claim)` (SHA-256 of
  whitespace-normalized casefolded text); `language`: en; bounded `verdict` above.
- `caption` <=2200 characters: scoped verdict, source URLs, date checked and explicit
  AI-assisted research/design disclosure. `reviewer`, `evidence_summary` nonempty.
- Explicit editorial/ready/evidence booleans and high-impact flag as above.
- UTC-aware `claim_date`, `reviewed_at`, `created_at`, `expires_at`, `run_after`,
  `run_before`. Claim date <=30 days old, review <=7 days old, none future.
  Expiry <=30 days after creation. Run window <=24 hours, inside expiry and campaign.
- `sources`: 1–10 objects with url, title, publisher, supports, published_at,
  checked_at, supports_claim_analysis=true. Publication <=30 days old, checked <=7.
  Do not substitute a date-checked value for an old publication date.
- `screenshot_provenance`: original_url, publisher, context, captured_at, sha256,
  original=true, rights_reviewed=true. Hash the actual capture; never invent it.
  If the archive or original cannot be inspected, hold the draft. Current executable
  URL policy rejects query strings; do not silently strip meaningful archive queries.
- `image`: url, mime=image/jpeg, width, height, sha256. Baseline sRGB JPEG, approved
  default 1080x1350, <8MB. HTTPS anonymous fetch, public DNS, no redirects, credentials
  or URL query. Use immutable commit-addressed raw GitHub URL after card upload;
  calculate SHA-256 from final JPEG bytes.

## Rendering and verification commands

Inspect the approved source image with the available image viewer first. Rendering
requires Pillow only in the producer environment; publishing and tests use stdlib.
No rendering command should run on uninspected or unavailable source bytes.

```sh
python3 render_card.py approved-input.png cards/claim-id.jpg
python3 -m unittest discover -s tests -q
python3 publisher.py queue.json
python3 pilot.py --config campaign.json --queue queue.json
```

`render_card.py` preserves the full composition, converts to sRGB, fits within
1080x1350 on white without cropping, and writes a baseline JPEG without metadata.
Inspect its pixels after conversion; confirm readability and that claim/evidence
labels cannot be confused. A structural dry run does no network, authentication or
truth verification. The eventual live preflight verifies anonymous image bytes and
source readability, identity and quota; any uncertainty stops publication.
