# Authorized first manual test — ready for parent dispatch

Workflow: Bounded Instagram pilot, file .github/workflows/publish.yml.
Branch: main. Input: confirm_first_live_test=true. Repository variable
PUBLISHING_ENABLED must be the string true. INSTAGRAM_ACCESS_TOKEN already exists;
do not display, read back or copy it. The connector has no workflow-dispatch method,
so parent browser owns exactly one manual dispatch after latest CI succeeds.

Selected queue contains ONLY the separately reviewed Full Fact Hormuz/Bangladesh
card. AFP card is not queued and its denied fetch route stays stopped. Campaign
start/end are in campaign.json, exactly30days apart, end exclusive. Queue run window
is6hours; dispatch before run_before. No schedule is enabled.

After dispatch, inspect the public runner receipt for media_id/permalink and the
publishing-state sent row. The independent following step verifies duplicate guard
with no token, zero Instagram calls and no state writes. Do not dispatch again if
outcome is uncertain. Preserve all state and explicitly reconcile before any retry.
A post-send permalink lookup failure is not permission to republish. Confirm the
actual Instagram post separately. Do not enable schedule before successful proof
and independent research producer readiness.
