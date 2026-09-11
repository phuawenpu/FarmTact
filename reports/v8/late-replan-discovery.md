# Crop-cycle identity regression discovered during final review

On 11 September 2026, the source review and a new 84-day HTTP test exposed a planner identity defect in `daily-bed-cpsat-v2`. Candidate IDs used a sow offset relative to the current horizon. Replanning from a later date could assign the same ID to a different absolute crop cycle. Because recorded simulation tasks use allocation ID plus task name, this could suppress a later cycle’s events while its numerical trace still generated harvest.

The first execution of `tests/gameplay/test_simulation_execution.py::test_late_replans_preserve_distinct_crop_cycles_and_every_harvest_task` failed in 19.13 seconds: `bed-04-caixin-13` referred to sow dates 2026-09-21 and 2026-09-28. The test uses real local planning, the normal simulation routes through an ASGI HTTP test client, an 84-day horizon, and replans after days 7 and 42. It checks allocation identity, task uniqueness, harvest events and inventory lot identity. This is a synthetic regression, not a farm trial.

Independent inspection also established that harvest lots reused allocation IDs, allowing a collision with an imported opening lot. A lot collision could preserve aggregate mass while making provenance ambiguous and preventing a subsequent replan from validating its inventory. Both identity paths are corrected in `daily-bed-cpsat-v3`; the final regression artifact records the post-fix result.

The earlier 56-day, one-replan trial is retained as evidence of its narrower executed path. Its pass did not establish correctness of every later crop-cycle identity.
