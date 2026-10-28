# Source verification when runner access is unavailable — proposal only

The current implementation still requires an anonymous source HTTP 200 before
publishing. No exception, fallback, access bypass or live activation is enabled by
this proposal. An access refusal must not trigger retries through alternate hosts,
proxies, user-agent impersonation, authentication or URL variants.

If the official site is independently readable through the parent's already supported
authorized browser, a separately reviewed architecture can verify a fresh evidence
record rather than pretending the runner fetched the page. This must be an explicit
policy change with recorded parent approval, not an automatic response to failure.

Proposed gate for a specifically approved source:

- Exact canonical source URL and known runner result recorded without claiming
  runner availability. Preserve publication date and genuine last-observed time.
- A current official-page read by an identified independent automated reviewer,
  separate from the card producer; notes explaining what was actually inspected.
  Reading the original source and inspecting the approved screenshot are distinct.
- An immutable reviewed evidence record in the public repository, SHA-256-bound to
  source URL, stable claim ID, narrow verdict, final caption hash, JPEG hash and exact
  screenshot-provenance hash. Record observation timestamps and renderer/browser
  route truthfully; never substitute filesystem save time for capture event time.
- Require evidence observation within 24 hours at publication, full source metadata,
  independent reviewer identity, source-to-claim reasoning and contextual rights
  review. A missing, stale, changed or unapproved record fails closed.
- Keep anonymous public JPEG availability/hash/dimensions as a mandatory runner
  check. Preserve all account, quota, campaign, idempotency and uncertainty gates.
- Select this mode explicitly per source only after parent approval. Default stays
  live-source-fetch. Do not silently downgrade failed live fetch to cached evidence.

A repository commit gives tamper evidence but does not prove a reviewer actually
read a page. Trust remains in the authorized independent research/review process
and restricted repository writers. Do not claim cryptographic proof of truth.
Do not reproduce entire source articles; retain minimal factual notes, attribution
and approved necessary screenshots. A past read alone is insufficient for the
proposed 24-hour gate. No new browser source access is attempted by this executor
as a way around a runner denial.

Exact runner failure is now confirmed HTTP 403. Implementation and activation
remain deferred pending parent review of the concrete evidence record and policy. No quality gate is removed here.
