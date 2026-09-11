# V11 guided-planning frontend implementation

The V11 web entry point is a guided farm-production mission aligned with the organizer brief. It reuses the existing farm records, numerical strategies, adviser artwork, simulation state, edition-aware API transport, idempotency handling and advanced rooms.

The journey presents confirmed customer orders, crop timing and bed occupancy before calculation. Its outcome cards place booked fulfillment, unmet demand, expired waste, closing stock and simulated margin together. Council review is an explicit advisory checkpoint; numerical schedules remain available when review is unavailable. Simulation is labelled synthetic and cannot authorize real farm work.

The disruption form separates residual future-demand assumptions from explicit booked-order changes. Seasonal assumptions are dated, scoped to sheltered hydroponics and labelled as synthetic sensitivities. The resulting page compares the saved schedule and replanned strategies under the same changed conditions and lists physical allocation changes without claiming an improvement.

The browser stores only the selected planning-session identifier. Authoritative state stays server-side and is restored through `GET /api/v1/planning-sessions/{id}`. Existing Farm, Council research, Farm tools, Crops, Data, Outcomes and Setup views remain reachable as advanced rooms.

The root edition chooser and the in-app edition switcher sort numbered editions in descending numeric order. This intentionally places V11 before V10 and V9 rather than relying on registry order or lexicographic text sorting; the registry's `latest` value still controls the latest-edition badge.

Validation commands:

```text
cd apps/web && npm run build
node tests/browser/v11_planning_journey.mjs
```

The browser journey performs real V11 numerical operations and deliberately does not invoke provider-backed Council review. It verifies reload persistence, explicit Council gating, distinct demand/order inputs, dated seasonal assumptions, simulation safety, same-condition comparison, responsive widths and absence of provider requests.
