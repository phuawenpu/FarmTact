# V12 farmer workflow and active-edition retention

V12 is published at https://farmtact.fly.dev/v12/ from immutable source
`9fd57898b8a4e3b69a40c3abf03895f0fcb05daf`. V11 retains its own frozen
image and independent state. [Implementation/evidence](../../reports/v12/implementation.md)
and the [requirement map](../../reports/v12/requirements-evidence.md) record tested
scope, original failures and remaining qualitative/source limitations.

The farmer loop is observe → discuss → decide → approve → act → verify → replan.
Imports and extracted documents are candidates until reviewed. Photo observations
have separate authority and never establish yield or authorize an operation.
FinancialDataConnector normalizes CSV/XLSX/accounting rows with reconciliation;
signed corrections name a unique sale/expense reference. Unsupported crops remain
accounting-only, outside the four-recipe numerical planner.

Conversation proposals retain the owned message hash, snapshot/result reference,
original suggested actions and hash of farmer-reviewed changes. Creating a draft
does not change the plan. Apply & Recalculate executes local numerics. Explicit
approval binds the completed result/revision and generates idempotent tasks. Task
reports and corrections append immutable events; corrections revalidate complete
checklist/quantity/status requirements and recalculate recovery state.

Guided Council prompt/validator/functional contracts are V4, context V4 and schema
V3. Crop composition claims cite crop-specific facts. Capacity findings require
cost/area/labour; balanced findings require service, waste/stock and margin groups.
Provider abstention and absent external sources remain partial. Conversation
prompt/context V7 and validator V6 separate booked demand from all modeled demand.
Typed frozen facts are checked; qualitative interpretations remain explicitly
unverified and advisory. No model conclusion applies a proposal or enables a farm
operation. Actual trial limitations are retained rather than hidden by valid references.

The active manifest contains previous/latest only. Historical releases remain
append-only and control numbering. Candidate checks preserve the public pair;
publication atomically advances it. Retired routes return 410 for all methods.
Cleanup snapshots first, checks actual applied Machine/container state and excludes
active/staged editions and gateway controls. The host-side release tool has a
postpublication Fly CLI compatibility correction; it does not replace V12's image.
See [the release runbook](../deployment/editions.md).
