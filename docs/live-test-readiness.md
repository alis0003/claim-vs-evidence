# First live test status — source preflight blocked

Parent authorized exactly one live test and confirmed the Actions secret exists.
No secret value was read by this executor. Active Instagram permissions are reported
as basic + publish only. Ruleset 26012232 was independently read: Active, exact state
branch, deletion and force-push blocks only, no bypass. Existing ledger was empty.

AFP source https://factcheck.afp.com/doc.afp.com.D3XP2T4 was readable through browsing
on 28 October and still supports the narrow reviewed claim. The draft run window
was refreshed, preserving original evidence/capture/save dates. Card pixels, original
crop hash and contextual rights review remain unchanged. Caption explicitly separates
card review on 27 October from source recheck on 28 October.

GitHub public source preflight run 40640152359 failed with `http_failure` at
2026-10-28T05:48:50Z. This is the first source GET in preflight, before image retrieval
or any Instagram API call. The implementation emitted no HTTP status/body/header;
therefore redirect vs refusal cannot be determined from retained logs. No access
bypass or repeated source fetch was attempted. Source preflight is now manual-only
to prevent automatic repeated requests on unrelated commits.

Offline CI run 40640152179 passed (76 tests). Campaign active remains false,
activation_at/end_at remain null, operational queue empty, live workflow disabled,
and live_test_completed false. Token readiness flag now reflects parent's confirmed
secret storage, without implying source readiness. No Instagram POST or GET was made.

Next: diagnose the source response through an authorized read-only route without
bypassing a refusal. Do not loosen source validation or substitute unverified evidence.
Once public source and image gates pass, activate the exact 30-day window and queue,
then parent browser dispatches the manual workflow once with explicit confirmation
and PUBLISHING_ENABLED=true. The connector has no workflow-dispatch operation.

The live runner now has bounded GET-only container-readiness polling and verifies
id/permalink after durable sent state. A post-send permalink lookup failure reports
sent_but_permalink_unverified_no_republish. Never repeat the publishing POST to fix
receipt lookup. Independent duplicate guard remains credential-free.
