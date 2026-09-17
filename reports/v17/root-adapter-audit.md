# V17 root adapter audit

Scope: read-only inspection of the V17 changes to `IntegratedApp`, `IntegratedHistory`, `IntegratedPlan`, `IntegratedRecords`, `lib/cards`, and edition/local-storage isolation. The audit used commit `c06438b` plus the current working-tree integration. It made no API requests and invoked no inference. The still-running PostgreSQL regression log was not used as acceptance evidence.

## Findings found and corrected

### 1. Mission primary actions lost their contextual destination

**Severity:** functional navigation regression.

In the audited commit, `IntegratedCards.primary()` opened Records for approved work by setting only `surface = "records"`, and opened History for a simulation result without a target. Consequently:

- **Review sandbox work / Open work records** lands at the Records default home card, whose default category is Setup, instead of the saved tasks named by the action.
- **Open simulation history** lands at History’s default Saved plans index instead of Simulations.

The smaller contextual buttons already used the correct targets. The corrected primary branches now set Tasks and Simulations targets and capture the stable primary label and scroll before changing surface, including keyboard invocation.

### 2. A direct Plan target did not initialize its matching index

**Severity:** latent state mismatch.

The original change initialized `view` from `initialTarget` but always initialized `index` to `0`. Detailed Plan cards intentionally hide category Previous/Next navigation, so this was latent rather than a visible `1 of 5` defect. The corrected initialization maps every `PlanTarget` to its matching category index. The **Dated schedule** path now renders a canonical `plan:strategies:*` strategy card with no Objectives fallback.

The ordinary no-target default remains index 0.

### 3. Unsaved Plan assumptions were edition-scoped but not farm/session-scoped

**Severity:** recoverable cross-workspace draft contamination.

The audited commit used one `farmtact:v17:planning-assumptions-draft` key for every ordinary planning session. Switching to a newly imported farm or another planning attempt in the same browser could show the previous session’s unsaved assumptions in the new session. The server still validated any submitted proposal, so this was not an authorization bypass, but it conflicted with the explicit reviewed farm transition and could make an old draft appear current.

The corrected implementation waits for the active session, loads `planning-assumptions-draft:<session id>`, and writes only when the draft owner matches that session. The explicit “import saved settings” action remains the cross-session transfer mechanism.

`IntegratedRecords` now combines the V17 edition namespace with the active session ID for farm-import, manual-entry, task-result, and correction drafts. Task-specific names retain task IDs as an additional boundary.

## Confirmed sound behavior

- `CURRENT_EDITION` is `v17`; `editionStorageKey` selects an explicit edition from the URL or falls back to V17. Existing immutable `/v15` and `/v16` routes therefore keep separate namespaces.
- `lib/cards` defines typed, read-only targets for every adapter. These types grant no mutation authority and retain the existing server-owned `CardAction` eligibility contract.
- Records direct targets initialize their requested view and select a requested stable entity after async data load. Back closes a directly targeted view rather than detouring through Records home.
- History maps its six direct targets to the corresponding index before loading. Direct list/preferences/help views close to their caller; ordinary entry still begins at Saved plans.
- `IntegratedApp` keeps nested Records→Plan, Records→Waste Rescue, and Experiments→Research parents mounted while hiding them, then restores focus and scroll. Recovery additionally waits for the workflow refresh event before a second focus restoration.
- Persisted shell navigation includes `toolTarget`, direct-tool origin, mission index, and scroll, all under the edition and session-specific navigation key.

## Verification after fixes

The final candidate `index-CHDAS7Ra.js` passed all 16 checks in `reports/v17/adapters.json` with every API write blocked:

1. The emphasized approved-task action opened Tasks & results, and Back restored the same mission primary focus.
2. The emphasized recorded-simulation action opened Simulations, and Back restored the same mission primary focus.
3. The contextual schedule action rendered a canonical strategy card without an Objectives fallback.
4. Two labelled GET-only planning-session fixtures retained distinct cash-capacity drafts (`111` and `222`) across reloads. Neither inherited the historical unscoped draft.
5. Records ignored the historical unscoped farm JSON draft and created a key scoped to the selected fixture session.

The compact Knowledge category change was also rechecked by the separate agent workflow: `reports/v17/personas/v17-acceptance.json` passed 10/10 on the same build, including Specialists selection, direct/invite/Council actions, focused reload, and discussion-to-proposal provenance.

Human usability remains unverified by this source audit.
