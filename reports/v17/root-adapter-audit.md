# V17 root adapter audit

Scope: read-only inspection of the V17 changes to `IntegratedApp`, `IntegratedHistory`, `IntegratedPlan`, `IntegratedRecords`, `lib/cards`, and edition/local-storage isolation. The audit used commit `c06438b` plus the current working-tree integration. It made no API requests and invoked no inference. The still-running PostgreSQL regression log was not used as acceptance evidence.

## Findings

### 1. Mission primary actions lose their contextual destination

**Severity:** functional navigation regression.

`IntegratedCards.primary()` opens Records for an approved plan or saved tasks by setting only `surface = "records"`; it does not set `{ records: { view: "tasks" } }`. It likewise opens History for a simulation result without `{ history: "simulations" }` ([IntegratedCards.tsx, lines 529–537](../../apps/web/src/components/IntegratedCards.tsx)). Consequently:

- **Review sandbox work / Open work records** lands at the Records default home card, whose default category is Setup, instead of the saved tasks named by the action.
- **Open simulation history** lands at History’s default Saved plans index instead of Simulations.

The smaller contextual buttons use `openContextTool` with the correct targets, so this affects the emphasized action-area path rather than target contracts generally. The primary branches should call the same targeted-opening helper or set `toolTarget` before changing surface.

### 2. A direct Plan target does not initialize its matching index

**Severity:** visible state/metadata mismatch.

`IntegratedPlan` initializes `view` from `initialTarget` but always initializes `index` to `0` ([IntegratedPlan.tsx, lines 18–21](../../apps/web/src/components/IntegratedPlan.tsx)). A contextual **Dated schedule** target therefore renders Strategies while its position remains `1 of 5`, corresponding to Objectives. Its static card/index identity is also derived from that stale index while the view body is Strategies.

Map `PlanTarget` to the matching index at initialization, as History already does in `open(section)`. The ordinary no-target default should remain index 0.

### 3. Unsaved Plan assumptions are edition-scoped but not farm/session-scoped

**Severity:** recoverable cross-workspace draft contamination.

The planning draft uses one `farmtact:v17:planning-assumptions-draft` key for every ordinary planning session ([IntegratedPlan.tsx, lines 21–24](../../apps/web/src/components/IntegratedPlan.tsx)). Switching to a newly imported farm or another planning attempt in the same browser can show the previous session’s unsaved assumptions in the new session. The server still validates any submitted proposal, so this is not an authorization bypass, but it conflicts with the explicit reviewed farm transition and can make an old draft appear current.

Scope the draft by the active planning session or immutable farm/version identity after the session loads. Preserve recoverability within that scope. A deliberate “import saved settings” action can remain the cross-session transfer mechanism.

`IntegratedRecords` now correctly adds the V17 edition namespace through `editionStorageKey`, preventing V15/V16 draft reuse. Its farm-import and generic manual-entry drafts remain shared within the V17 browser namespace; task-result and correction drafts additionally include task IDs ([IntegratedRecords.tsx, lines 227 and 255–257](../../apps/web/src/components/IntegratedRecords.tsx), [line 298](../../apps/web/src/components/IntegratedRecords.tsx)). Generic Records draft sharing is lower risk than planning assumptions but should be documented if intentional.

## Confirmed sound behavior

- `CURRENT_EDITION` is `v17`; `editionStorageKey` selects an explicit edition from the URL or falls back to V17. Existing immutable `/v15` and `/v16` routes therefore keep separate namespaces.
- `lib/cards` defines typed, read-only targets for every adapter. These types grant no mutation authority and retain the existing server-owned `CardAction` eligibility contract.
- Records direct targets initialize their requested view and select a requested stable entity after async data load. Back closes a directly targeted view rather than detouring through Records home.
- History maps its six direct targets to the corresponding index before loading. Direct list/preferences/help views close to their caller; ordinary entry still begins at Saved plans.
- `IntegratedApp` keeps nested Records→Plan, Records→Waste Rescue, and Experiments→Research parents mounted while hiding them, then restores focus and scroll. Recovery additionally waits for the workflow refresh event before a second focus restoration.
- Persisted shell navigation includes `toolTarget`, direct-tool origin, mission index, and scroll, all under the edition and session-specific navigation key.

## Verification needed after fixes

Use a read-only browser check for the two navigation corrections:

1. From the approved-task mission card, activate the emphasized action and assert the first visible Records view is Tasks; Back returns to the same mission action and scroll position.
2. From the recorded-simulation mission card, activate the emphasized action and assert History opens Simulations; Back restores the same origin.
3. Open the strategy schedule contextual action and assert Strategies content and `2 of 5` agree.
4. Seed two session-scoped planning drafts and confirm each session reloads only its own value. This can use localStorage and GET fixtures; it does not require proposal submission.

Human usability remains unverified by this source audit.
