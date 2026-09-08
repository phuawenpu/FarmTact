# Independent conversation backend review

Reviewed 2026-09-08. Scope: `services/api/conversations.py`, `services/api/conversation_store.py`, and `tests/gameplay/test_conversations.py`. The review covered frozen snapshots, tenant isolation, reply graphs, invitations, council limits, repairs, evidence/tool validation, event reconnect, replay, persistence, partial failure, idempotency, and inference budgeting. No live provider call was made.

## Resolution verification

### 1. Resolved: successful validation now states its limited scope

The backend now rejects digit-form and common spelled numeric, date, percentage, and relative-date claims in advisor prose. Quantities are authoritative only when rendered separately from immutable tool references. A successful qualitative reply receives `validation_status="references_verified"`, `validation_scope="reference_membership_and_supported_controls"`, and `interpretation_status="unverified_advisor_interpretation"`. The public conversation policy exposes the same boundary.

This deliberately does not claim that a cited evidence record entails an advisor's interpretation. The frontend's evidence cards preserve that distinction and render referenced values with their declared units. The previous numeric-coincidence probe (`Balanced margin is 32 SGD` citing labour hours) is now unsupported because numeric prose is prohibited; an unrelated but permitted evidence reference may establish membership only, while the interpretation remains visibly unverified.

Actual scope caveat: `references_verified` guarantees reference membership and supported scenario-control targets. It does not validate evidence entailment, agronomic correctness, causal claims, or recommendations. Those qualitative claims remain advisor interpretation and cannot authorize a farm or scenario change.

The earlier spelled-quantity residual is resolved. A conservative deterministic scanner now flags common number and ordinal words, named months, and relative calendar forms. Regression cases for `twelve percent`, `September eighth`, and `tomorrow` all remain visibly unsupported even when the reply supplies a valid frozen tool reference. Ambiguous lowercase `may` is not treated as a month by itself; capitalized `May` followed by a date value is treated as a calendar claim.

### 2. Resolved: transcript capacity is preflighted before enqueue

`_enqueue` performs its idempotent-request lookup first, then rejects when `current_count + 1 + len(roles) > 120`. The regression test starts with 119 messages, attempts an eight-turn council request, receives HTTP 409, and confirms that no user message was appended. Idempotent retries can still retrieve the original request at the cap.

## Verified behavior

- Conversations freeze a tenant-owned farm or completed scenario snapshot, include source context and tool/evidence references, and do not follow later farm mutations.
- Conversation creation and request creation are serialized and idempotent. PostgreSQL tests cover concurrent creation, concurrent request enqueue, message/event sequencing, and restart persistence.
- A conversation allows only one queued/running response at a time. User messages and request records are persisted atomically.
- Typed follow-ups can target the advisor who made a referenced statement. Invitations require an advisor message and create a two-sided reply chain. Council discussions are fixed at eight turns, and direct/council structured-output repairs are limited to one/two calls respectively.
- Completed messages survive provider failure or process interruption. Interrupted work is not requeued, preventing ambiguous paid-call repetition.
- Missing credentials and exhausted global budget produce visible blocked states without a provider call. Reserved but unused calls are released on normal completion/failure paths.
- Unknown tool/evidence/highlight references, unknown action targets, and numeric/date/percentage prose in digit or common spelled forms are visibly unsupported. Proposed actions never execute from the conversation runtime.
- Valid tool-reference quantities are rendered as separate evidence cards with metric-specific values and units. Qualitative prose retains the `unverified_advisor_interpretation` label even when its references are members of the frozen context.
- GET, listing, replay, and event resume are tenant-scoped. Replay uses stored messages and makes no inference reservation. Event cursors resume without duplicate sequence IDs.

## Checks executed

- `.venv/bin/python -m pytest tests/gameplay/test_conversations.py -q` — 18 passed.
- Numeric-coincidence regression — confirms a wrong-unit numeric claim is unsupported even when its value matches a cited field.
- Spelled-claim regressions — confirm spelled percentages, named dates, and relative dates remain unsupported.
- Transcript-cap regression — confirms a council request at 119 existing messages is rejected before any new message is stored.
- Deterministic claim scanner — confirms digit-form percentages and ISO dates plus common spelled quantities and relative/named dates are rejected.

The SQLite suite gives strong coverage to frozen context, bounded provider calls, replay, reply relationships, interruption, budget exhaustion, tenant isolation, conservative quantity handling, and multi-turn capacity. PostgreSQL conversation persistence and concurrency are covered by the same suite when `TEST_POSTGRES_URL` is supplied. No live provider call was made in this review.
