# V19 Council decision brief

V19 is the next unpublished FarmTact edition. It keeps V18's ordinary synthetic
farm, one card shell, server-owned planning and revision-bound workflows. It changes
how a calculated choice is read and reviewed.

## Decision surface

Each calculated strategy card now has a small **Decision brief**. It keeps the
comparison summary visible and puts the remaining detail behind an ordinary native
`Decision details` disclosure:

- dated allocation count and affected grow spaces;
- the frozen projection/result basis;
- the existing all-demand coverage and shortfall measures;
- a compact Planning Council state;
- up to five server-derived allocation dates, crops and projected kilograms.

The brief is a presentation of the frozen planner result. It is not a saved proposal,
a claim of a physical outcome, or a new agricultural model. Preview remains labelled
**Preview—not saved**.

The strategy action row stays at three controls. It is now:

1. **Explain**, which reads only stored facts;
2. **Ask Council about this plan** when no finding exists, or **Read Council findings**
   once a review has recorded them;
3. **More**, which opens the existing five-card tools index.

The Council action is optional. Asking it calls the existing revision-bound Planning
Council review route through its existing admission and provider controls. Reading a
recorded review, browsing strategy cards, swiping, expanding details and replaying
history never invoke a provider or mutate the farm.

## Council contract

The shared frontend `FarmCard` contract carries a `CouncilReviewBinding` for every
calculated strategy card. It records the planning session, frozen revision and result
identity, review state, finding count, and whether an explicit provider submission is
still required. `BoundCard` exposes that contract as `data-council-binding` for
accessibility and browser verification; the metadata cannot grant mutation authority.

The existing Planning Council card remains the one full review surface. V19 makes its
binding explicit, identifies the frozen result, keeps the seven-role roster and typed
facts, and renders recorded proposed actions as advisory next actions. It clearly
states that Council cannot alter assumptions, approve work, or authorize physical
operations. Returning uses the existing focused return path to restore the originating
strategy card.

## Recovered information patterns

V11's useful context selection, role roster, consequence panel and explicit next step
are restored as compact decision information rather than as another required room.
V12's reviewed state boundaries remain unchanged. V13's immediate card comparison,
scene focus and tactile action dock remain unchanged. Crop profiles, source records,
specialist threads, Data Explorer, Council research, records and history stay reachable
through the V18 integrated tool decks.

Council research remains a distinct frozen experiment: discussion, reviewed edit,
local calculation, challenge and saved result. It does not become an approval route for
the ordinary plan.

## Verification boundary

V19 must pass the existing full Python/PostgreSQL regression, generated-contract and
frontend build checks, responsive card journeys at 360, 390, 430 and desktop widths,
reduced-motion checks, exact staged-image browser checks, operator acceptance and
append-only release preservation before publication. Provider review is not exercised
by browser browsing checks; it requires an explicit action and remains subject to the
shared admission budget. Human usability is still not established by those checks.
