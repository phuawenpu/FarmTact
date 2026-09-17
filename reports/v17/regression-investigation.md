# V17 initial regression and corrected verification procedure

The first full run finished with 797 passed, one skipped, four failures and three setup errors in 885.66 seconds. Preserve `regression.txt` and `regression.xml` as the actual initial result.

Six failures/errors occurred while Vite was rebuilding its output directory and the API factory tried to mount `apps/web/dist/assets`. These tests did not reach their domain assertions. The V9 report had documented this same verification race; the first V17 run failed to follow that frozen-build procedure. Final verification freezes the local production dist for the entire full PostgreSQL run. No public image or assets were altered by the local build.

The remaining case, `test_stale_approval_results_corrections_restart_and_tenant_isolation`, reached approval and received 409 (`Only a feasible calculated strategy can be approved`). Its isolated rerun passed in 34.62 seconds (`approval-recheck.xml`). This is not proof of the initial failure's cause. No feasibility guard or test assertion was weakened. The final full run must pass with the stable build and without competing browser numerical jobs.

The final run uses the separate local PostgreSQL database `farmtact_v17_regression_final`; production, ordinary browser fixtures, shared abuse counters and provider budgets are untouched. Provider credentials are removed from the test process. No acceptance result is inferred merely from the isolated recheck.
