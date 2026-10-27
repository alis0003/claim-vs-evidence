# First live test and approved protection scope

No campaign activation, rule change, secret access or publication is performed by
this document. The first manual test does NOT require live_test_completed=true.
That flag is only checked for schedule events. A mocked end-to-end runner test proves
manual mode can reach one publishing attempt while the flag remains false.

## Ordered activation after parent instruction

1. Confirm INSTAGRAM_ACCESS_TOKEN was securely inserted and set only its readiness
   flag; no token is copied into code, chat or files. Confirm the reviewed draft and
   original evidence record. Source, image and identity checks must still succeed.
2. Confirm the state branch protections below; verify pinned genesis and empty or
   correctly reconciled journal. Never reset state merely to retry.
3. At the explicit parent live-test step, copy the reviewed draft into queue.json,
   refresh its run window within evidence freshness/expiry limits, set activation_at
   to the actual pilot start and end_at exactly 30 elapsed days later, exclusive.
   Set active=true. Do not set live_test_completed yet.
4. Enable only the reviewed manual publishing workflow and repository variable
   PUBLISHING_ENABLED=true. Keep schedule commented. Run workflow_dispatch once with confirm_first_live_test=true.
5. Only after confirmed publication AND acknowledged sent state, record successful
   live test and set live_test_completed=true. Uncertain outcomes require explicit
   reconciliation, never rerun a POST blindly. Complete the independent duplicate guard check below. Scheduling may then be
   enabled in a separate reviewed workflow change; the manual-test template has no schedule.

## Exact approved protection scope — application pending confirmation

Repository: alis0003/claim-vs-evidence only. Branch ruleset named
`Protect publishing state`; enforcement Active; include exactly
`refs/heads/publishing-state`; no exclusions or bypass actors. Enable:

- Restrict deletions (`deletion`).
- Block force pushes (`non_fast_forward`).

Leave linear history, restrict updates, restrict creations, required PRs, required status checks,
signed commits and deployment prerequisites off for this state-only branch. They
would block direct checkpoint commits or require additional bypass privileges.
Do not grant bypass to a user/App, add collaborators, expand repository access,
change account-wide permissions or apply these settings to another branch/repository.
The publishing job requests only repository Contents write using its temporary
GITHUB_TOKEN; offline CI retains no permissions and no secret inputs.

The user explicitly approved only deletion and force-push blocks. A separate browser
worker owns applying those two restrictions; this executor makes no settings changes.
Do not add linear-history requirements or bypass actors. Confirm the applied settings
with the parent and read-only evidence before activation. Public repository branch rulesets are available
on GitHub Free; do not purchase a plan. Verify the actual resulting rules read-only.

Limit: these rules prevent deletion and rewinds, not merge commits or malicious edits
in a new fast-forward commit by an authorized writer. Repository writers and trusted
workflow code remain security boundaries. Do not imply that an actor-only write
restriction has been enforced. No extra bypass permission is proposed.

Official reference checked 27 October 2026:
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

## Independent duplicate-run verification

The disabled manual-test template scopes INSTAGRAM_ACCESS_TOKEN only to the
publishing step. Its following verification step has no Instagram or GitHub token:
it anonymously fetches the public state branch, records the exact commit SHA and
runs verify_duplicate.py against that immutable snapshot and the unchanged one-card
queue. The checker uses the real Publisher duplicate path with an API object that
raises on ANY call and a journal that rejects ANY write. It requires a released owner,
matching queue fingerprint, sent phase, container ID and media ID. Success means
already_sent with zero API calls and zero state writes. It never retries publication.

The parent independently reads that recorded public state commit, compares claim ID,
fingerprint, media/container IDs with the unchanged queue, and checks the one real
Instagram post. If the result is ambiguous, do not dispatch a second live run merely
to test deduplication. Keep all uncertainty held for explicit reconciliation.

This offline duplicate-path proof plus immutable state inspection is the first test's
safe duplicate verification. Any optional second actual workflow dispatch requires
separate parent instruction after confirmed sent state; never edit the claim ID,
queue fingerprint or journal to obtain a successful test. All 30-day/window/identity
and quota protections still apply to the original publishing path.
