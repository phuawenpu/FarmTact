Current work, 16 September 2026: V12 is in private acceptance; V11 is the sole
public application. V1–V10 workers and storage are retired with recovery and
preservation evidence. Read reports/v12/acceptance-status.md and
docs/v12-implementation-plan.md before the historical handoffs below.

# Fresh-workspace handoff — 11 September 2026

This handoff was prepared before deleting the development workspace. GitHub and
Fly are the durable records; local Sprite checkpoints, databases, browser sessions,
credentials and `/tmp` build tools must not be assumed available.

## Resume here

1. Clone `https://github.com/phuawenpu/FarmTact.git` and check out current `main`.
2. Read `AGENTS.md`, `CODEX_START_PROMPT.md`, `MASTER_AGENT_PROMPT.md`, the build and
   DeepSeek runtime specifications, and `docs/execution-plan.md`.
3. Read `reports/v11/implementation.md` and
   `docs/technical/v11-guided-production-planning.md` for the final evidence and
   known limitations. The comprehensive HTML/PDF and screenshots are committed.
4. Follow README's local setup using `requirements.lock.txt`, `npm ci --prefix
   apps/web`, and a fresh development database. Do not copy production state into
   an unauthenticated development server. Recreate credentials through the new
   environment's authorized secret mechanism; no credentials are in this handoff.
5. Verify current GitHub/Fly capability using normal authenticated CLIs. Process
   credentials in the deleted workspace do not transfer through Git. Do not print
   credentials or use gateway discovery as a test of GitHub/Fly access.

## Published state

- Latest edition: https://farmtact.fly.dev/v11/.
- Starting screen: https://farmtact.fly.dev/ lists V11 down to V1.
- Frozen application source: `37802adbc9010bc80a50869ef725285a119af3f3`;
  source tag: `farmtact-v11`.
- Image: `registry.fly.io/farmtact@sha256:e82ba02912d7a716ec4a4588a6fc83721cb361549d9fbbefc92eae1ce439cf7d`.
- Release publication commit: `1646ba4`; final implementation-report commit:
  `cd113f1`. Later handoff/docs commits do not change the published application.
- Fly app `farmtact`, Singapore Machine `2871575b4544d8`, volume
  `vol_vdejexpzm8ydn5x4`. Gateway and eleven editions share the host; edition
  databases/caches/progress are isolated, while abuse and inference limits are
  shared. Deleting the development workspace does not delete these Fly resources.
- Canonical manifests: `config/releases/registry.json`, `config/releases/v11.json`,
  `config/hosting/shared.json`. Always recheck the remote registry before changes.
- Next unused edition at handoff: **V12**. Never overwrite V11 or prior editions.
  Use `docs/deployment/editions.md`, not a generic production `fly deploy`.
- Local publisher reservation metadata is archived in
  `reports/v11/publication-reservations.json`; all recorded reservations are
  published. No unpublished candidate or deployment remains pending. The remote
  registry remains authoritative for choosing the next number.

## Verification and outstanding work

The V11 report records 643 regression passes with one skip, 63 subsequent
control/gateway/deployment passes, 24 local browser checks, 20 staged live journey
checks with five DeepSeek requests and no repairs, three passing capacity pairs,
and all eleven public health/source plus prior-ten preservation checks. Public
smoke passed 11 assertions. No numerical or provider work remains running from
these completed trials. Temporary local development services are disposable.

Prioritize the known Council presentation defect: rejected individual findings
are not clearly withheld/labeled, and overall completion currently depends on a
validated Chair rather than all active specialists. Add a rejected-specialist /
validated-Chair browser case, suppress invalid decision advice and show partial
status. The passing live V11 case had no rejected findings and does not validate
this branch. Implement any app fix as the next immutable edition.

Sustained planning latency remains variable (127.76 seconds for the live journey's
initial calculation); paired short-load checks do not establish sustained capacity.
The farm/seasonal models remain synthetic, and real-record calibration, manual
planning benchmarks and farmer comprehension studies remain open. Older V8–V10
AI failures are preserved and not certified by the bounded V11 Council.

All runtime inference stays on the allowlisted DeepSeek gateway. Keep the shared
48-request daily cap and explicit review/replay rules; never reset counters for
testing. The historical engagement ledger at handoff totals 90 actual requests
(44 local, 46 public), including prior failures and repairs. This is an audit
count, not a prediction of the remaining quota in a future session. Real farm
operations remain disabled.
