# First live test and proposed state protections

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
   PUBLISHING_ENABLED=true. Keep schedule commented. Run workflow_dispatch once.
5. Only after confirmed publication AND acknowledged sent state, record successful
   live test and set live_test_completed=true. Uncertain outcomes require explicit
   reconciliation, never rerun a POST blindly. Then scheduling may be enabled.

## Exact proposed ruleset — not applied

Repository: alis0003/claim-vs-evidence only. Branch ruleset named
`Protect publishing state`; enforcement Active; include exactly
`refs/heads/publishing-state`; no exclusions or bypass actors. Enable:

- Restrict deletions (`deletion`).
- Block force pushes (`non_fast_forward`).
- Require linear history (`required_linear_history`).

Leave restrict updates, restrict creations, required PRs, required status checks,
signed commits and deployment prerequisites off for this state-only branch. They
would block direct checkpoint commits or require additional bypass privileges.
Do not grant bypass to a user/App, add collaborators, expand repository access,
change account-wide permissions or apply these settings to another branch/repository.
The publishing job requests only repository Contents write using its temporary
GITHUB_TOKEN; offline CI retains no permissions and no secret inputs.

These restrictions are consistent with the approved secure setup of this new
repository, but the approval did not enumerate ruleset/admin settings. Treat this
as a concrete proposal for parent confirmation before applying; no settings were
changed or privileges broadened here. Public repository branch rulesets are available
on GitHub Free; do not purchase a plan. Verify the actual resulting rules read-only.

Limit: these rules prevent deletion, rewinds and merge commits, not malicious edits
in a new fast-forward commit by an authorized writer. Repository writers and trusted
workflow code remain security boundaries. Do not imply that an actor-only write
restriction has been enforced. No extra bypass permission is proposed.

Official reference checked 27 October 2026:
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
