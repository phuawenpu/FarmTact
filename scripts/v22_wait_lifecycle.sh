#!/usr/bin/env bash
# Run one real local V22 lifecycle only after the ordinary admission window
# expires. This intentionally observes the existing limiter and never resets it.
set -euo pipefail

while [ "$(psql -h /tmp/farmtact-pg -d farmtact_v20_dev -Atc "select count(*) from abuse_rate_counters where expires > extract(epoch from clock_timestamp())")" != "0" ]; do
  sleep 30
done

exec env \
  BASE_URL=http://127.0.0.1:4199 \
  EXPECTED_EDITION=v22 \
  NORMAL_MOTION=1 \
  ARTIFACT_DIR=/tmp/v22-lifecycle-final \
  REPORT_PATH=/tmp/v22-lifecycle-final/report.json \
  VIDEO_DIR=/tmp/v22-lifecycle-final/video \
  node tests/browser/v22_lifecycle.mjs
