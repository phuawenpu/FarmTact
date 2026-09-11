# V9 first full regression: concurrent asset rebuild

The first isolated PostgreSQL run collected 607 tests and ended with 603 passed,
three failed and one skipped in 436.38 seconds. Every failure occurred while
constructing the API's static-files mount: `apps/web/dist/assets` temporarily did
not exist during a concurrent Vite rebuild. None reached the assertion for its
named mission/news behavior. The complete result is preserved in
[the original XML](archive/full-regression.asset-build-race.xml).

Affected cases:

- `test_mission_gate_preserves_alternatives_and_budget[failed_before_claims]`
- `test_scenario_freezes_news_and_advisor_uses_the_same_records`
- `test_mission_freeze_and_replay_keep_news_separate_from_farm_hash`

The verification procedure now freezes the production browser build before the
final whole-repository rerun. Do not run Vite's destructive output-directory
rebuild concurrently with API tests or a local service that reads that directory.
Published images contain the finished build; no production asset directory was
removed by this local test activity. This failed run is retained rather than
reported as a full pass.
