# Fly deployment verification

Verified 2026-09-08. Deployment status: **PASS**. Primary URL: https://farmtact.fly.dev/.

## Deployed resources

- Existing app: `farmtact`; region: `sin`.
- Machine: `d8d2060c074438`, one shared CPU, 2 GB RAM.
- Encrypted volume: `vol_rnzewn8jd6055ner`, `farmtact_data`, 3 GB, mounted at `/data`; seven-day snapshot retention.
- Image: `registry.fly.io/farmtact:deployment-01M20VRAD976174EGEPD1E9E5D`.
- Image digest: `sha256:3476a9baa69db5aa55331502af0b49713354bb6255d2166f4b84ce00c8a24504`.
- Runtime verified: Python 3.13.15, PostgreSQL 18.6. Remote SQL confirmed PostgreSQL listens only on `/tmp/farmtact-pg`, with TCP disabled.
- DeepSeek credential supplied through encrypted Fly runtime secrets; no provider credential is built into the image.

## Verification evidence

- Final remote image build and deployment succeeded, including native dependency imports and actual app import as the unprivileged runtime user.
- Fly HTTP health check passes. HTTPS bootstrap responds with ten crop profiles and seven public sources. Session cookies carry Secure, HttpOnly and SameSite=Strict.
- Twelve targeted deployment, TLS-cookie and tenant-isolation tests passed. The independent deployment review includes ten focused tests and resolved source findings; see [review](agents/fly_deployment_review.md).
- [Real Fly browser suite](fly_browser.json): **44/44 passed**, zero console/page errors, widths 360/390/430/1280. Numerical mission `48d3380896b41cb5489b1e7b64994067` and disruption replan `3645dc64a74ac4658f76a48f617abb66` both reached `ACCEPTED_FOR_SIMULATION`, with `council_status=not_run`. Mobile board, dialog and resource screenshots were inspected.
- [Persistence check](fly_persistence.json): the same session and saved farm version 2 survived an actual image deployment using the existing volume.
- Deployment logs show application shutdown completed and PostgreSQL shut down cleanly at 15:56:55 UTC, then reused the cluster and became ready at 15:57:01 UTC. The API completed startup at 15:57:17 UTC.
- Fresh public ingestion produced 205 rows across seven validated sources, with zero connector failures: 145 weather observations, 45 forecasts and 15 trade rows. This is a separate, later snapshot from the original Sprite report.

## Actual provider run and limits

The [Fly integrated council report](fly_integrated_demo.json) is **INCOMPLETE**, not an accepted end-to-end council run. Actual synthetic-label vision and all six DeepSeek council roles completed. The critic included an unsupported `0.5` threshold; local claim validation rejected it and the backend withheld acceptance. The run finished `NO_FEASIBLE_PLAN` with `council_status=claims_rejected`, and stored replay passed. No dependent replan ran. Eight of nine reserved requests were consumed; one unused reservation was released. This verifies real provider connectivity and rejection behavior, not successful council acceptance or the correctness of every natural-language assertion.

The separate numerical browser workflow passed acceptance and replanning without inference. Earlier successful Sprite council evidence remains historical evidence for that recorded run and is not substituted for this Fly result.

This deployment remains an autonomous synthetic development instance. One machine has no high availability; a volume snapshot restore has not been tested. Fresh Fly sessions receive new synthetic tenants and do not inherit Sprite session data. The [runbook](../docs/deployment/fly.md) documents redeployment and repeatable verification.
