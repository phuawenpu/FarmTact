# FarmTact public-demo security

This document describes application-enforced controls, not a claim of immunity to
prompt injection or distributed denial of service. The public application remains
an anonymous synthetic farming demo; it does not authorize real farm operations.

## Request admission

All limits are server controlled. A caller cannot change them through an API body,
cookie, query parameter or prompt. Counters are atomic PostgreSQL records on the
existing persistent volume and survive application restarts and redeployments.
Over-limit requests return HTTP 429 and `Retry-After` before parsing or queueing AI
work. If admission storage is unavailable, requests fail closed with HTTP 503.

| Scope | Limit |
| --- | --- |
| AI-triggering POSTs, per source IP/network | 6 per minute and 20 per hour |
| AI-triggering POSTs, per authenticated demo session | 12 per hour |
| New demo sessions, per source IP/network | 30 per hour |
| New demo sessions, entire app | 100 per hour |
| API requests, per source IP/network | 600 per minute |
| Application writes, per source IP/network | 60 per minute |
| Non-API application/probing requests, per source IP/network | 30 per minute |
| Admitted application/API requests, entire app | 3,000 per minute |
| Event-stream openings, per source IP/network | 12 per minute |
| Active event streams, current server | 4 per source IP/network; 32 total |
| Event-stream lifetime | 360 seconds; reconnect reads saved events |
| HTTP connections, current server | 64 concurrent; 5-second idle keepalive |

AI limits cover conversation messages, invitations, council requests, planning
missions and replans, including failed probes and repeated idempotent requests.
Planning routes conservatively share these limits even when a particular request
disables inference. Numerical scenario routes remain available under the normal
write limits. Limits use fixed windows starting at the first request; limits can
reset at a window boundary. Replays and reads do not consume AI-request quotas.
Fixed health checks and static artwork/assets are exempt from database admission.
Stream detection covers both the `Accept` header and supported boolean query forms.

In Fly, only a configured private transport peer may supply `Fly-Client-IP`.
Uvicorn forwarding-header rewriting is disabled. Caller-supplied `X-Forwarded-For`
is never used as identity; outside the Fly configuration, only the transport peer
is used. IPv4-mapped addresses normalize to IPv4 and IPv6 clients share their /64
allowance. IP-derived identifiers are HMACs using a persistent server-only key;
raw IPs and cookies are not stored in rate counters. Changing cookies does not
reset IP limits, and changing IPs does not reset the same session's quota.
Networks shared by multiple people share the IP quota. Fly's documented header
semantics are described in [Request headers](https://fly.io/docs/networking/request-headers/).

## Authentication, request and browser boundaries

Demo sessions use random bearer cookies with only their hashes stored in the
database. Cookies are Secure on Fly, HttpOnly and SameSite=Strict. Server-side
authentication expires after 24 hours; merely retaining an old cookie cannot
extend it. Sessions are anonymous workspace identities, not verified user accounts.

Protected application requests use the configured Fly host and exact write origin;
cross-site Fetch Metadata writes are rejected. Non-browser clients may omit Origin,
but still require an owned session and pass admission. Imports have a 1 MiB body
cap, including chunked uploads, and a 15-second body-read timeout. Request models
forbid unrecognized fields. Public OpenAPI, Swagger and ReDoc endpoints are disabled.
Disabling those endpoints reduces casual discovery; authorization never depends
on an endpoint being secret.

Queries and mutations use authenticated tenant predicates and composite tenant
foreign keys. Unowned object IDs return not-found responses. SQL uses parameterized
SQLAlchemy operations. Public file routes serve fixed artwork/build directories,
not arbitrary paths. React renders advisor prose as text. CSP permits scripts and
connections only from the application origin, prohibits framing, and is paired
with `nosniff`, same-origin referrers and no-store API responses.

## Inference and injection boundaries

- The server alone holds the provider credential. No generic provider proxy is
  exposed. V8's fail-closed caller manifest distinguishes active product/API callers
  from diagnostic routes, and every current text/native-vision role requests exact
  canonical `deepseek-flash`. Only the reviewed DeepSeek HTTPS origin, paths and mappings
  are accepted; redirects and alternate-provider fallback are disabled.
- Every application inference request sends a stable opaque DeepSeek `user_id`
  derived from its random internal tenant ID. Neither IP nor session cookie is
  sent as that identifier. DeepSeek documents its intended isolation behavior in
  [Rate Limit & Isolation](https://api-docs.deepseek.com/quick_start/rate_limit).
- User text, source material and earlier messages are untrusted context. They
  cannot choose provider configuration, execute SQL/shell commands, register tools,
  read environment variables or select another tenant's snapshot.
- The frozen V4 conversation projection admits at most 48 typed facts, 24
  qualitative references, 16 prior turns and six evidence records, with a hard
  120,000-character serialized prompt limit. Explicit frozen research inputs are
  retained even when ordinary ranking caps are reached. This bound can omit other
  relevant context, so an adviser must abstain when the admitted context cannot
  answer the question; projection is not a claim of universal coverage.
- Model JSON is locally schema validated. Quantity/date outputs select typed frozen
  fact IDs; server code renders their value, unit, entity, period and snapshot hash.
  Qualitative refs are disjoint. Invalid
  suggestions stay blocked. Qualitative interpretations remain unverified even
  when their references are recognized. No model-generated HTML is executed.
- Advisor proposals use only the declared bounded scenario controls. They open
  editable experiments and cannot directly mutate the main farm. Simulation
  acceptance is backend-only and independently checks numerical feasibility.
  A mission's explicit `required` policy withholds incomplete/unsupported Council
  findings; `advisory` can retain numerical acceptance while exposing those issues.
- The generic gateway tool helper accepts only names supplied by trusted Python
  callers and strict argument models. No HTTP route lets a caller register a tool
  or provide an executor. Future executable tools require a separate authorization
  review and server-derived tenant scope.
- Python egress restrictions allow DeepSeek and the configured database only.
  This is a defense-in-depth hook, not an OS firewall or native-code sandbox.

The existing hard **48 provider-call UTC daily ceiling** remains shared by all
sessions. Each run also limits request count, output-token reservations, duration,
response bytes and concurrency. Direct exchanges have one repair at most; conversation councils
have seven advisor turns plus two repairs. Unused reservations reconcile against
the original reservation day, including jobs crossing midnight. Recorded replay
and reconnect never authorize another provider call. HTTP quotas count requests;
one accepted council HTTP request can make multiple bounded provider calls.

## Operational limits

Application rate limits are not an edge WAF. A sufficiently distributed attacker
can use different IPs and anonymous sessions, compete for the global allowance,
or saturate infrastructure before application checks run. Stronger production
access would require verified accounts or an access allowlist, plus edge bot/WAF
controls. Fly notes that its proxy does not itself act as a WAF in its
[deployment troubleshooting guide](https://fly.io/docs/getting-started/troubleshooting/).

Prompt injection can still influence qualitative advice or an adviser's
recommendation. Reference membership does not prove factual entailment. Restricting
model capabilities, validating results and retaining numerical authority limit
the consequences; a system prompt alone is not a security boundary. This follows
the layered approach in [OWASP's prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

Rate-limit logs contain bounded rule names, not prompts, credentials or raw IPs,
and repeated notices are suppressed for a minute. Expired rate-counter rows are
periodically removed. The detailed code audit is in `reports/ai_boundary_audit.md`;
release-specific test and live-probe evidence is in `reports/security_hardening.md`.


## Audit clarification — 11 September 2026

This security inventory does not establish adviser factual correctness. The
[provider report](technical/ai-provider-and-council.md) distinguishes schema and
reference checks from entailment, current caller paths from registered capabilities,
and archived probes from current availability. [The backend audit](technical/game-backend-and-state-machines.md)
details job, proposal, challenge and selection state boundaries and their gaps.
Strict deadline cancellation, monetary reservation and infrastructure egress remain
separate requirements; the implemented limits must not be described more broadly.

Anonymous tenant cleanup is an explicit operator action: see the [retention runbook](runbooks/retention.md). The command defaults to a dry run and 30 retained days, enforces a minimum of seven days and a maximum of 500 candidate tenants per invocation, skips any tenant with queued/running mission, scenario, conversation or research work, and preserves shared budgets and security records. Twelve isolated tests cover dry-run, complete child deletion, active/recent retention and input bounds. It is not automatically scheduled.
