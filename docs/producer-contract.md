# Native research producer contract

Read this contract, `campaign.json`, `queue.sample.json`, and `publisher.py` before
producing anything. Never invent queue fields or populate unknown evidence values.
Research runs in flexible mornings in Asia/Kolkata. Quality comes first: zero posts
is acceptable, there is no daily volume guarantee and no invented/weak debunks.
No third-party AI API, paid service, password bot or private Instagram endpoint.

## Campaign authority

`campaign.json` is the single canonical configuration. `active` reflects the authorized manual-test pilot; check its current value.
`activation_at` must be a timezone-aware ISO timestamp and `end_at` must be EXACTLY
30 elapsed days later; end_at is exclusive. Do not activate or move these dates.
Do not modify secret-readiness, initial-review or live-test flags. Schedule triggers
are not punctuality guarantees; the runtime rejects publication outside this window.
While inactive, prepare reviewed drafts only. Do not publish or promote initial queue.

## Allowed producer writes

Only `drafts/**`, `cards/**`, `sources/**`, and append-only additions to `queue.json`
are permitted. Do not modify code, workflows, campaign configuration, state branch,
secrets, account settings, repository settings, tests or completed queue records.
Never overwrite an existing stable claim ID to evade deduplication. Independent automated evidence/editorial review must also check for semantically
duplicate claims with different wording. Record the distinct producer and reviewer
identifiers and actual review notes; never imply a human reviewed the work. Do not write
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
- `review_provenance`: mode=independent_automated, distinct producer_id and
  reviewer_id, and nonempty review_notes. reviewer must equal reviewer_id. Record
  the actual independent evidence/editorial assessment in sources; never invent
  reviewer identity or label automated review as human approval.
- Explicit editorial/ready/evidence booleans and high-impact flag as above.
- If actual claim-post date is unknown, leave claim_date=null; use
  claim_date_basis=dated_fact_check_documents_circulation, a YYYY-MM-DD
  circulation_observed_date, matching circulation_evidence_url and explicit
  claim_date_note. The date must match the reviewed fact-check publication date,
  within30days. This documents circulation by that date, not the post timestamp.
- UTC-aware known `claim_date`, `reviewed_at`, `created_at`, `expires_at`, `run_after`,
  `run_before`. Claim date <=30 days old, review <=7 days old, none future.
  Expiry <=30 days after creation. Run window <=24 hours, inside expiry and campaign.
- `sources`: 1–10 objects with url, title, publisher, supports, published_at,
  checked_at, supports_claim_analysis=true. Default role recent_reporting: publication <=30 days old, checked <=7.
  Do not substitute a date-checked value for an old publication date.
- For claim_screenshot only, `screenshot_provenance`: original_url, publisher, context, captured_at, sha256,
  original=true, rights_reviewed=true. Hash the actual capture; never invent it.
  If exact capture time was not recorded, captured_at may be null with genuine
  saved_at_utc, timestamp_basis=filesystem_save_exact_capture_unrecorded and a
  timestamp_note explicitly distinguishing file save from capture event. Never infer
  a timezone for an archive label. Recent save time is a freshness check, not proof
  of event time. Original source pixels/hash still require independent review.
  Source/provenance URLs preserve public document query selectors (type, view,
  format, page, id, article, lang, date, q). Credential/signature/redirect parameters,
  duplicate keys and nested URLs are rejected. Never strip meaningful queries.
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


## Append-only history and readiness confirmation

Keep sent/expired jobs unchanged in queue.json. Offline CLI validates identity and
window structure across the full history, rejects duplicate IDs anywhere, and fully
validates only currently due jobs. Do not change old run windows to make CI pass.
Future jobs receive full evidence validation when due; a clean offline run never
asserts that skipped future evidence is publication-ready. The durable sent ledger
is never removed/reset by queue validation.

Licensed-format producer fresh-run capability is still unconfirmed. Only the parent may update
producer_fresh_run_verified, producer_readiness_record and scheduled_publication_enabled.
Scheduled publication remains disabled until the independent fresh-run proof is checked.

## Source roles and date precision

Existing sources retain recent_reporting semantics. A source may instead declare
`evidence_role=primary_documentary` when it is authentic primary documentary
evidence, with `primary_source=true`, `publication_date_verified=true`, nonempty
`publication_date_basis` and `documentary_relevance`. Preserve its original date;
older publication is allowed only with at least one distinct
`evidence_role=recent_fact_check`, `independent_fact_check=true` source published
within30days. Every source must be checked within7days and support the narrow claim.
These attestations require actual independent review; schema validation cannot
detect a fabricated factual date. Primary documents cannot supply circulation dates.
Claim/circulation freshness, review freshness and run windows remain unchanged.

For date-only source metadata use `published_date=YYYY-MM-DD` and omit/null
`published_at`; never invent midnight or a timezone. At most one may be present.
Date-only recency uses calendar days; existing timestamps retain elapsed-time
recency. Publication must precede the source check; future or contradictory dates
fail. Unknown publication date is not accepted as meaningful timed evidence.
Supplementary undated URLs may be cited as context but cannot replace the required
dated evidence or be assigned a guessed date.

## Licensed visual formats — required for every new publication

This format approval does NOT authorize retrying the denied HTML2Shell screenshot.
Do not promote that candidate, recycle it as a workaround, or invent a false claim
for the available CRS-35 jellyfish photo. Find a distinct evidence-verified story.
A true verdict is valid when supported; never assume every claim is false.

Each new job needs `visual_provenance` (see queue.sample.json and the single-object
candidate-photo.sample.json). `kind=claim_screenshot` requires genuine screenshot
provenance AND established reuse rights. `kind=evidence_photo` requires the claim
as text and a separately rights-cleared photo; omit screenshot_provenance entirely.
Visible and caption label must be exactly `Claim screenshot`, `Illustrative photo`
or `Evidence photo` as appropriate. Never call an illustration a screenshot or
present an unrelated photo as evidence. Evidence photo requires a nonempty
`evidentiary_connection` and `evidence_source_url` matching reviewed sources.
An illustrative photo supports presentation only, never the factual verdict.

Required fields: source_url, license_url, rights_evidence_url (public HTTPS),
creator, attribution, license_exact, rights_basis, transformations, context,
asset_sha256 and rights_checked_at (actual check within7days). Record exact
asset-specific terms and their source, not just a general site licence. Supported
identifiers: CC0-1.0, CC-BY-4.0, CC-BY-SA-4.0, public-domain, explicit-permission.
These are schema categories, not a determination that an arbitrary asset qualifies.
Public-domain needs evidence for this asset; explicit-permission needs a public,
non-sensitive permission record covering this use. Never publish private emails.
Do not claim a licence or permission when unknown; hold the candidate instead.
Set reuse_rights_verified, social_publication_permitted and adaptation_permitted
true only after independent evidence establishes each. Attribution must appear
verbatim in the caption. CC-BY-SA-4.0 additionally requires output_license with the
same value and that identifier in the caption; reviewer must assess compliance.

`visual_review` binds reviewer_id to the distinct editorial reviewer, jpeg_sha256
to final output, and caption_sha256 to SHA256 of exact UTF-8 caption bytes (including
newlines). It needs actual reviewed_at within7days, notes, label_visible=true and
context_verified=true from actual pixel review. Any visual/caption change requires
new review/hashes. Screenshot asset hash and source URL must match capture record.
Photo acquired_at is actual acquisition within30days; photo_captured_at is actual
exposure timestamp if known, otherwise null with honest capture_date_note. Never
infer exposure time from download time. Older authentic photos are allowed when
context is correctly labelled; claim and source freshness are unchanged.

Run `python3 validate_candidate.py candidate.json` on EVERY new candidate, then
`python3 validate_candidate.py candidate.json --anonymous-preflight` in a supported
runner. This explicitly enforces current rights gates. Anonymous preflight checks
source, licence/rights metadata and JPEG availability; it cannot establish truth or
rights by HTTP success. Stop on denial; no spoofing or alternate-route retries.
Legacy queue records stay unchanged for history/deduplication. `validate` and the
queue-history CLI can parse legacy records, but the live publisher blocks a new
POST unless visual rights validation passes. `validate_ready` is the required new
candidate schema. Do not treat old offline history validation as promotion proof.

Scheduling remains disabled until an independent fresh producer demonstrates this
format with a genuine eligible candidate and verified promotion, or an explicitly
reviewed alternative readiness proof. Empty routine runs are safe and expected.
No guaranteed daily volume; the November27 exclusive cutoff is unchanged.
