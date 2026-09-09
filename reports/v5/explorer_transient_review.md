# v5 explorer transient HTTP 500 review

Reviewed 9 September 2026 from the v5 service log and the browser harness. No
request was replayed and no provider or new numerical run was used.

## Finding

The failures were frontend document requests while the shared `dist` directory
was temporarily absent during a concurrent web build. They were not failures of
a Data Explorer API or numerical worker.

The v5 service recorded two exceptions:

| UTC time | External route | Upstream route | Response | Server error |
|---|---|---|---|---|
| 16:18:24.687 | `GET /v5` | `GET /` | HTTP 500, plain `Internal Server Error` | `FileNotFoundError`, followed by `RuntimeError: File at path apps/web/dist/index.html does not exist` |
| 16:24:49.621 | `GET /v5` | `GET /` | HTTP 500, plain `Internal Server Error` | The same missing `apps/web/dist/index.html` error |

The gateway removes the edition prefix and forwards `/v5` to `/` on the v5
process. The application root route returns `FileResponse(dist/'index.html')`.
That route was registered because `dist` existed when the process started, but
the build workflow later removed the file. The final `index.html` mtime is
16:24:51.175 UTC, about 1.55 seconds after the second exception. The matching
trace is in `/.sprite/logs/services/farmtact-v5.log`; it passes through
`services/api/app.py:185` and ends in Starlette `FileResponse` at
`services/api/app.py:373`.

The first exception coincided with the earlier explorer browser attempt. The
second coincided with a separate infeasibility browser pass, whose screenshots
were being captured at 16:24:45–16:24:48. Because the service does not emit
access lines, the external route is established from the harness navigation,
the gateway prefix mapping, and the only application handler in the traceback:
the `/` document `FileResponse`. No API handler appears in either trace.

## Release interpretation

This is a real availability failure in the shared live-development workflow:
rebuilding directly into the directory served by a running process creates a
window in which navigation or reload returns 500. It does not show a defect in
saved snapshots, previews, scenarios, comparisons, exports, or numerical jobs.
The stable-build explorer rerun passed 73 checks with five completed numerical
jobs, no page errors, and no inference calls.

The published immutable edition image should not rebuild its assets in place,
so this exact trigger should be absent after deployment. Release smoke testing
must still occur after the image is fully assembled and started.

## Recommendation

For local and future multi-process edition serving, build into a staging
directory and switch the complete asset tree atomically, or stop traffic while
replacing it. At minimum, serialize builds and browser suites so a live suite
never reads `dist` during deletion and recreation. An application fallback that
returns a controlled 503 when `index.html` is unavailable would improve the
failure mode but would not remove the availability gap. Do not classify a
successful retry as sufficient evidence on its own; retain the log check above
in release review.

The v5 explorer harness now changes the supplied Secure session cookie only
when its configured base URL explicitly uses HTTP. HTTPS targets preserve the
production cookie attributes.
