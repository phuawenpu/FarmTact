# V15 completion audit — 17 September 2026

Scope is the full user-approved V15 replacement plan, not only onboarding. The
implementation is frozen at `a5ab2a8`; later commits record evidence and handoff.
This audit supplements the predevelopment capability inventory in
`docs/v15-capability-checklist.md`. Report paths below are relative to this directory.

## Original plan requirements and authoritative evidence

| User plan | Implemented sources | Verification |
| --- | --- | --- |
| 1. One shell, ordinary demo, three actions, swipe/keyboard, contextual tools, reviewed import and exact return | `IntegratedApp`, `IntegratedCards`, `ToolCard`, `BoundCard`, `lib/cards.ts`; `planning_sessions.py` guidance and atomic farm transition | `responsive-guide-contract.json`, `bound-card-contract.json`, `context-import-browser.json`, `shell-reload-return.json`, `card-return-browser.json`, four complete `browser-cards-{width}.json` journeys |
| 2. Planning: every supported strategy, constraints, comparisons, review/apply/recalculate/approve/reserve/inverse | `IntegratedPlan`, `IntegratedCards`; existing planner and `farm_workflow.py` | `plan-history-browser.json`, `plan-history-gaps-browser.json`, `native-assumptions-browser.json`, `strategy-facts-browser.json`, `reservation-eligibility-browser.json`, `release/operator-acceptance.json` |
| 2. Records/work: imports, Inbox, evidence, orders/beds/inventory, tasks/results/corrections/recovery | `IntegratedRecords`; existing ingestion, document extraction and workflow services | `records-browser.json`, `records-extended-browser.json`, `records-gaps-browser.json`, `records-approval-guard-browser.json`, `simulation-replan-browser.json`; full ingestion/document/task adversarial regression |
| 2. Knowledge: crop limits, freshness, evidence, deterministic explanations, adviser histories and Council | `IntegratedKnowledge`, `IntegratedCards`; existing validated conversation/Council gateway | `knowledge-browser.json`, `bound-card-contract.json`, `release/staged-browser.json`; recorded response/withheld/outage cases are labelled fixtures, not live provider-quality evidence |
| 2. Experiments: quests/scenarios, frozen branches, explorer, dataset generation/exports, forecast settings, research and Waste Rescue | `IntegratedExperiments`, `IntegratedResearch`; existing scenario/dataset/research/workflow APIs | `tools-browser.json`, `experiment-gaps-browser.json`, `explorer-browser.json`, `research-browser.json`, `scenario-controls-browser.json`, `context-import-browser.json` |
| 2. History/preferences: plans, discussion/simulation/event replay, new attempts, motion/audio/help | `IntegratedHistory`; frozen planning-result replay and existing history APIs | `history-replay-browser.json`, `plan-history-gaps-browser.json`, `simulation-replan-browser.json`, `release/public-browser.json` |
| 3. Stable identity/provenance, versioned guidance, authoritative explanations/transitions, preview/save distinction | `lib/cards.ts`, `BoundCard`, planning/workflow contracts and services | `bound-card-contract.json`; PostgreSQL guidance, transition, inverse, concurrent apply/approval tests; `browser-cards-widths.json`, `final-motion-review.json` |
| 3. Explicit provider admission only, retain drafts and reconcile uncertainty | API admission middleware, existing allowlisted gateway, request client, integrated deck submissions | Full security/admission/provider regression; Records/Knowledge/Research fault fixtures; `terminal-reconciliation-browser.json`; exact staged SSH failure reconciled before resume |
| 4. Functional, responsive, numerical, security, recovery and release verification | Executable browser suites and isolated PostgreSQL tests, generated types, clean production build | `regression-final.xml`: 792 passed/one skip; `local-acceptance-gate.json`; `frontend-build.json`; exact-image operator20/browser26; public67/isolation13/preservation9 |
| 5. Immutable sole-current release, preserved history/data/counters, no state merge | `config/releases/v15.json`, active/registry manifests, archive-only publisher and gateway | `release/runtime-image.json`, `release/public-browser.json`, `release/public-isolation.json`, `release/public-preservation.json`, `release/retention.json` |

## Evidence boundaries

- The full four-width journeys use the immediately preceding shell build; the
  final eligibility-only delta has 34 targeted checks at all four widths. The
  exact final image passes staged mutation acceptance and four-width public reads.
- Normal-motion video and start/mid/end frames show recorded consequences;
  reduced motion retains the same facts. These do not establish comprehension.
- Accounting supports unsupported crop records with warnings; only the existing
  four crop recipes have numerical support. Waste Rescue ends at its supported
  read-only alternatives; no rescue execution API was invented.
- Saved provider answers and outage/withheld states are exercised with labelled
  recorded/transport fixtures. No new live provider quality is claimed.
- Shared preservation permits new durable acceptance records. The original
  restaging checker misclassified the running unpublished V15 database; its failed
  report is retained alongside the strict reviewed exception and the unmodified
  postpublication verifier's pass.
- Human usability remains unverified until representative new users are observed.
  Automated DOM accessibility and viewport checks do not establish real-device
  screen-reader or physical software-keyboard compatibility.
- Actual farm operations, autonomous inference, new rewards, drag-and-drop,
  custom transcription and new agricultural models remain outside this rewrite.

## Final audit follow-ups

The semantic audit found a genuine explanation defect: raw assumption JSON and
proposal-specific explanations reused across unrelated core stages. Completion is
not proven. The goal remains active; V16 will contain the correction because V15
is already immutable. Accessibility follow-ups pass their stated DOM/emulation
scope; physical device and representative-user validation remain unverified.
