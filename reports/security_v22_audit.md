# Live-deployment security audit — V22 (18 September 2026)

Scope: repository source on `main` and the running V22 Fly deployment
(`farmtact`, machine `2871575b4544d8`, image
`registry.fly.io/farmtact@sha256:e05b00a575983dfc79d83a41563c3cfe762579475e57d885df414d6705ecdee1`,
source commit `ac6c84d09d515eac51802138baceabf84a3c01a8`). Work was read-only: no
deployment change, no secret value read or printed, no provider/LLM call, no state
mutation. The authoritative policy text remains [docs/security.md](../docs/security.md).

Status: **findings open** — no fix has been deployed. The running V22 image is
immutable; any change requires the next contiguous edition (V23) plus a regenerated
shared-host configuration.

## F1 — HIGH. `/_control/*` is reachable from the public internet

The gateway establishes a "private only" boundary for the control plane in
`services/api/edition_gateway.py:45-54`: a request is rejected with
`404 {"detail":"Not found"}` unless it presents `Host: farmtact.flycast` **and** the
client address is classified private, or it matches the exact loopback +
`Host: farmtact-local-control.flycast:8080` local case. Address classification is
performed by `services/api/security.py:76-107`, which trusts a proxy-supplied
`fly-client-ip` header whenever the transport peer is loopback, `172.16.0.0/12` or
`fdaa::/16`, and otherwise falls back to the peer address.

Observed from a public client (this workspace, public egress `2a02:6ea0:d1b2::17`,
connecting to Fly's public VIP `2a09:8280:1::186:ceba:0`):

```console
$ curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
    -H 'Host: farmtact.flycast' -H 'Content-Type: application/json' -d '{}' \
    https://farmtact.fly.dev/_control/reserve
422     # control router reached: FastAPI validation lists edition_id, reservation_id, count, day

$ curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
    -H 'Host: farmtact.fly.dev' -H 'Content-Type: application/json' -d '{}' \
    https://farmtact.fly.dev/_control/reserve
404     # gate rejects without the overridden Host

$ curl ... -H 'Host: farmtact.flycast' -H 'Authorization: Bearer <invalid>' ...
401 {"detail":"Control authentication required"}   # route auth is reached
```

The 422/401 responses carry the gateway middleware's own headers
(`content-security-policy`, `x-content-type-options`, `cache-control: no-store`), so
the request passed the boundary middleware rather than being short-circuited. The
same probe from inside the running Fly machine reproduces both results (422 with the
override, 404 without).

Attribution was then measured rather than inferred. A single unauthenticated
`POST /api/v1/conversations/<id>/messages` was sent, and the live rate-limit rows in
the gateway's `farmtact_control` database (`abuse_rate_counters`, keys computed as
`HMAC-SHA256(ip_hmac_salt, "<rule>:<principal>")` per `services/api/security.py:118-125`)
were compared against candidate principals inside the container. Every affected rule
(`api_ip`, `write_ip`, `ai_ip_minute`, `ai_ip_hour`, `probe_ip`, `new_session_ip`)
matched the principal **`127.0.0.1`**, i.e. the deployment classified this public
request as loopback. Supplying the client's own `Fly-Client-IP: 203.0.113.7` did not
change the attribution, so the header is not attacker-controlled from here; the
defect is that address classification is used as the authorization boundary at all.

Impact: the private-only control surface (`/_control/reserve`, `/_control/consume`,
`/_control/release`) is reachable from non-local clients, is not rate limited on the
gateway, and is guarded only by the bearer `FARMTACT_CONTROL_SECRET`
(`hmac.compare_digest`, verified returning 401 for an invalid token). No valid
control action was attempted or achieved. The secret itself was never read or
printed.

Residual uncertainty (marked, not assumed): the audit could not send a request from
a network that Fly classifies as an ordinary public client. It is therefore
*confirmed* that at least two non-local client classes (this workspace over Fly's
public VIP, and a process inside the machine) reach the control router, and
*unconfirmed* whether a browser on a typical home connection is likewise attributed
a private address. The finding does not depend on that distinction because the
boundary is header/config derived rather than cryptographic.

Remediation: stop treating address class as authorization. Require the loopback
local case (or a dedicated non-public listener/port) for `/_control/*`, verify the
transport peer identity the proxy cannot rewrite, and add a gateway-level
authentication-failure counter. Keep the bearer secret as the authoritative check.

## F2 — MEDIUM. The gateway installs no abuse or rate-limit middleware

`AbuseMiddleware` is added only in `services/api/app.py:239-240` (the edition app).
`create_gateway()` never installs it, so `/`, static assets, the health probe and
`/_control/*` are uncounted on the public listener; repeated control probes returned
422/401 with no `429` at any point (~30 requests, F1). Fly ingress is the only
limiter on that path.

Remediation: install `AbuseMiddleware`/`AbuseLimits` on the gateway with a coarse
per-network probe rule plus a dedicated `/_control` auth-failure counter.

## F3 — MEDIUM. No HSTS header

`Strict-Transport-Security` is absent on `/` and `/api/v1/health`, and no
implementation exists in the repository. Port 80 returns `301` to HTTPS and cookies
are `Secure`, so the practical exposure is a first-request downgrade.

Remediation: add `Strict-Transport-Security: max-age=31536000; includeSubDomains` in
the gateway middleware (or set `force_https = true` on the canonical app config, which
the live service already deploys).

## F4 — LOW. Missing `Permissions-Policy`; `X-Frame-Options` only via CSP

Framing is already blocked by `frame-ancestors 'none'`, and `nosniff` plus
`Referrer-Policy: same-origin` are present. `Permissions-Policy` and legacy
`X-Frame-Options` are absent.

## F5 — LOW. One secret serves two trust relationships

`FARMTACT_CONTROL_SECRET` is both the `/_control/*` bearer
(`services/api/edition_control.py:142-146`) and the gateway-to-edition ingress header
(`services/api/edition_gateway.py:104`, `services/api/edition_ingress.py:16-19`).
Rotation requires re-staging both roles. Remediation: split an
`FARMTACT_INGRESS_SECRET` from `FARMTACT_CONTROL_SECRET`.

## F6 — LOW. Internal exception text is persisted and returned to its session

`services/api/planning_sessions.py:299` stores
`f'{type(exc).__name__}: {str(exc)[:400]}'` for unexpected job failures and returns
it through `public_session()` to the owning session. Contrast the fixed templates
used at `services/api/app.py:198-199` and `services/api/conversations.py:2376-2379`.
Read from source only; not reproduced live.

## F7 — LOW. Upload validation runs after the paid provider call

`services/api/farm_workflow.py:891` extracts the document (reserving a DeepSeek call)
before `save_source_blob` rejects an over-long filename or unsupported media type at
`:904-905`. Bounded by the AI quotas (6/minute, 20/hour per network), so this is a
cost-efficiency defect, not a breach.

## F8 — INFO. Static/health paths bypass admission by design

`services/api/security.py:199` exempts `GET`/`HEAD` on `/api/v1/health`, `/assets/`,
`/art/`, `/review-evidence/` and `/audio/`; combined with F2 those paths reach the
edition upstream uncounted. Cheap per request (most misses are 404s).

## F9 — INFO. Configuration drift and staged secrets

Root `fly.toml` does not describe the live machine (mount `/data` vs `/persist`,
1 vCPU/2 GB vs 4 vCPU/4 GB, `force_https = false`, no container block) and is now
annotated as legacy in the README. `fly secrets list` reports two staged (undeployed)
secret values. The dead `farmtact-local-v22.flycast` app registration resolves
in-container only through the `/etc/hosts` alias written by
`scripts/shared_container_entrypoint.py:146-149`.

## Verified clean

- **Secret hygiene.** Every blob in history (3 272 objects) was streamed and matched
  against provider-key, GitHub-token, Slack-token, private-key and
  `scheme://user:pass@` patterns: 30 hits, all triaged false positives (29 `task-<hex>`
  ids and one `${FARMTACT_DB_PASSWORD}` placeholder in `compose.yaml`). No tracked
  `.env`, key or credential file exists; `.gitignore`/`.dockerignore` exclude real
  env files. The live machine exposes no `FARMTACT_*` or DSN names in any response.
- **Transport and identity.** Only port 8080 is public; the edition port 8102 has no
  service. Port 80 redirects to HTTPS; cookies are `HttpOnly; Secure; SameSite=strict;
  Path=/; Max-Age=86400` and only SHA-256 hashes are stored. Session tokens are
  `secrets.token_urlsafe(32)` with server-side 24-hour expiry.
- **Request surface.** `/docs`, `/openapi.json`, `/redoc`, `/metrics`, `/debug`,
  `/server-status`, `/healthz`, `/.env`, `/.git/config`, `/static/` and other probe
  paths return 404 with no internals. No debug flag, stack trace, absolute path, SQL
  or env name appeared in any captured body.
- **Cross-origin behaviour.** An `Origin: https://evil.example` write returns 403 with
  no `Access-Control-Allow-Origin` (neither reflected nor wildcard); writes require the
  exact configured origin and host at both tiers.
- **Retired-edition isolation.** `/v1/`, `/v13/`, `/v20/`, `/v21/` return 410 for reads
  and for mutations (`POST /v21/api/v1/bootstrap` → 410 "Edition retired"). Edition
  containers reject non-health traffic without the authenticated gateway header.
- **Injection and file serving.** No SQL string interpolation, no `eval`/`exec`/
  `pickle`/`yaml.load`, no shell invocation from HTTP input. The only `FileResponse`
  targets are fixed `ROOT`-relative paths; uploads are media-type allowlisted,
  filename-sanitised, tenant-scoped and returned with `nosniff` plus a sandbox CSP.
- **Provider boundary.** No public schema, no generic provider proxy, no
  `chat/completions` passthrough. Egress is allowlisted to the reviewed DeepSeek
  origin, validated `.flycast` hosts and the configured socket database.

## Limits of this audit

Application and configuration review, not an infrastructure penetration test, edge
WAF assessment or dependency CVE scan (no network scanner was run; pinned versions
were read only). Two checks in the prior live-probe harness were **not** re-run here
because they deliberately consume the shared per-network AI allowance: the rotating
cookie/XFF admission probe and the forged-Fly-identity probe. Their last recorded
result remains [`reports/security_live_probe.json`](security_live_probe.json)
(8 September 2026, V8-era image) and should be re-run before the next publication.
Prompt injection, semantic adviser correctness and shared-capacity denial of service
remain outside this result, as documented in [docs/security.md](../docs/security.md).
