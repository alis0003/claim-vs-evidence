# Manual anonymous candidate check

Actions > Reviewed candidate anonymous preflight > Run workflow > main.
Supply a repository-relative candidate path, for example drafts/new-story/candidate.json.
The file must be independently reviewed and listed in sources/preflight-reviewed-candidates.json
with its exact SHA256, approved_for_anonymous_preflight=true, and a public review_record path.
The registry deliberately starts empty: existing held drafts are not approved merely by installing this checker.
Do not register iPhone, HTML2Shell, denied-source candidates, or denied assets.

A reviewer should assess the complete candidate and final JPEG/caption before registering
its exact bytes. Registering is a separate reviewed repository change; producer write scope
allows sources records but does not authorize falsely asserting completed review.
The existing validate_ready gate runs again at execution, including current time windows.
No input is inserted in shell code: the path is read from an environment variable,
checked against a strict path grammar, regular-file/no-symlink rules, and the hash-bound registry.
There is no arbitrary command or remote URL input. Main branch only.

Uses standard ubuntu-24.04, permissions {}, anonymous public Git fetch at the exact
workflow SHA, Python standard library and existing SSRF-protected preflight.
No secrets, token references, third-party Actions, publishing calls, artifacts, caches,
queue mutation or workflow schedule. No automatic retry; denial, unreadable metadata,
DNS failure, mismatch or timeout stops the job. Known denied routes/candidates are
blocked before fetching, including original X and the denied iPhone sources.
Do not replace the fetcher, use a proxy, edit another candidate to redirect an existing
workflow, or remove a hold to obtain a passing result.

Success establishes the checked bytes and anonymous availability at that run only;
it does not queue or publish. Promotion still requires every producer-contract gate.
Local tests: python3 -m unittest discover -s tests -q
