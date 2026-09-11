# V11 numerical worker validation

Date: 11 September 2026

## Result

The bounded numerical worker was exercised as an actual `spawn` process boundary. A seven-day, one-bed synthetic Farm with no batches, orders, history, or inventory completed the guided session calculation, returned all three strategies, selected a feasible schedule, and supplied the central execution trace within the test's 20-second bound.

The transport test returned a 4 MB result through the worker pipe and verified the complete frame. This exercises the auxiliary result-reader thread rather than treating pipe readiness as proof that an entire serialized result is already available.

Cancellation and an end-to-end deadline were each exercised against a sleeping child. Both returned within two seconds, terminated the child, and released the local admission gate. A subsequent spawned calculation succeeded in both cases. A child that closed without returning a result produced a bounded runtime failure and also left the gate reusable.

Cache validation used identical payloads under two tenant scopes. A repeated calculation in the same scope was a cache hit and returned a deep copy; mutation of the first caller's result did not corrupt the stored value. The other tenant scope was a cache miss. Tests clear the process-local cache between cases.

Every test checks that the `farmtact-numerical-job` child is gone and the admission lock is available at teardown. No provider call, HTTP request, database mutation, or real farm operation occurred.

## Verification

Executed in the repository `.venv`:

```text
pytest -q tests/gameplay/test_v11_worker.py
6 passed in 5.29s
```

## Limits

The gate is process-local. These tests establish one API process's admission, cleanup, transport, cancellation, deadline, and cache behavior; they do not establish host-wide admission across multiple API processes or historical editions. The 150-second production default is present in code but the tests use shorter explicit deadlines to exercise failure behavior without waiting. Sustained public Fly capacity remains a separate release criterion.
