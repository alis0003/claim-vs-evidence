# Remote state protocol and deployment boundary

The implemented `GitJournal` satisfies the publisher's journal interface. Tests use
independent temporary working repositories and a temporary LOCAL bare remote. No
GitHub repository, credential, account change or live Instagram call is involved.
The local GitJournal rejects hosted URLs; the separate GitHubJournal implements
the exact authorized repository through GitHub REST.
The active CI workflow has no publish path or secret input. The pilot CLI has an
explicit live option guarded by the inactive campaign and parent-readiness checks.

## Durable authority

A dedicated `refs/heads/publishing-state` branch has `state.json` with a version,
exclusive random owner ID and jobs keyed by stable claim hash. Rows contain only
public fingerprints, phases, timestamps, container IDs and media IDs. No caption,
source private content, token, header or credential is journaled. Commits retain
prior state for review; current state never deletes completed claims.

Provisioning is explicit: an authorized operator creates a reviewed genesis commit
with `{ "version": 1, "owner": null, "jobs": {} }` and pins its full commit ID in
deployment configuration. The adapter NEVER creates a missing state branch or
substitutes empty state. Every fetch must descend from that pinned genesis.

The implemented hosted transport restricts the
remote to the exact authorized public repository, prohibits credentials in URLs,
accepts ephemeral GitHub-scoped authentication without disk/log persistence, and
retains the same checkpoint protocol. The Instagram token and GitHub write authority
are different capabilities. Grant the eventual publisher only necessary repository
Contents write access; give neither API credentials nor write privileges to PR code.
Secrets must be injected only into the explicitly authorized trusted job.

Protect the state branch from force pushes, deletion and unauthorized direct edits;
only the journal writer and explicitly reviewed recovery should update it. If free
repository settings cannot enforce this, do not deploy under an assumption that
state is immutable. All other publishing clients must be disabled or coordinated.
Pinned genesis protects against unrelated/missing history, not a malicious authorized
writer removing records in a new commit. These trust assumptions are explicit.

## Checkpoint protocol

1. Fetch the exact remote head and validate schema and genesis ancestry.
2. Require no existing owner. Build a child commit with a fresh random owner ID.
3. Re-fetch and require the expected head. Push that child using an ordinary
   fast-forward push. Git atomically rejects a competitor's sibling commit.
4. Fetch again and require the exact new commit plus exact state contents. A command
   failure, timeout, rejection or different head is uncertain and poisons this
   adapter instance. Never automatically retry/rebase/merge/force-push.
5. Check identity, evidence, media and quota. Commit `creating` before media POST.
6. Commit returned container ID as `created`. A failure here prevents publish and
   leaves the remote intent unresolved, even if creation succeeded.
7. Verify readiness, dates and quota; commit `publishing` WITH container ID before
   media_publish POST. Recheck the run window after durable checkpoint latency.
8. Commit returned media ID as `sent`. Report success only after acknowledgment.
   If this final checkpoint is uncertain, do not claim the publication failed or
   succeeded. Require explicit reconciliation.
9. Release only this lock using the same expected-head protocol. Job records remain.

A lock fences the entire account, not just one claim, preserving rolling limits
across competitors. Every checkpoint uses the same expected chain; stale workers
cannot save after operator recovery changes the head. Only one lock acquirer can
reach an API POST. Lock release cannot erase uncertainty. There is no automatic
lease timeout, so abandoned runs sacrifice availability rather than risking duplicates.

## Recovery — explicit, never blind retries

Inspect a fresh adapter's `inspect()` result. Stop the original runner first; retain
the exact remote head and owner. `recover_abandoned_owner(expected_head,
expected_owner, stopped_confirmed=True)` releases only that inspected owner under
an optimistic head check; it preserves all job states. It does not assert success,
clear an intent, or retry anything. Stale head/owner inputs are rejected.

Then invoke `Publisher.reconcile(claim_id)` explicitly. It verifies account identity
and queries a known container. Only an unambiguous `PUBLISHED` status can be committed
as sent. FINISHED/IN_PROGRESS/ERROR/EXPIRED/missing status/read failure stay held.
If creation returned no durably known ID, manual investigation is required. Do not
clear the record merely to continue or assume a timeout means no remote effect.

A `created` row means the container ID was acknowledged and no publish intent was
recorded. `resume_created(job)` may publish this SAME container after fresh checks;
it never recreates it. `creating` and `publishing` rows can never use this path.
If a publish intent push was accepted but its acknowledgment was lost, the remote
publishing intent remains quarantined even though no POST may have happened. This
intentional false-positive hold is the safe consequence of distributed uncertainty.

A resumed worker must restore the journal from the remote, not a runner cache or
artifact. Do not wire SQLite as a fallback. A missing/unreadable remote branch,
failed checkpoint, changed head or orphaned owner must stop the run. The hosted adapter preserves these checks. The publishing workflow remains disabled;
there is no automatic publication path to bypass them.

## Hosted transport implementation update

`github_journal.py` now implements the authorized fixed repository's REST Git
transport. It reuses the same owner/state/recovery protocol, creates blobs/trees/
commits, updates the ref with force=false and confirms exact remote contents.
No git subprocess receives a token. The HTTP Authorization header is restricted to
api.github.com; errors are fixed codes with no response body/headers/token logging.
The local Git transport remains file-only. Hosted end-to-end validation and protected
branch setup are pending repository availability; local mocked success is not a
claim that GitHub deployment has succeeded.

Official GitHub references checked read-only for this implementation:
https://docs.github.com/en/rest/git/refs#update-a-reference
https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
