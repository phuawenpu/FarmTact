# Mobile navigation and independent reviewer panel

User goal: improve awkward mobile dragging; have ten distinct reviewer agents play
both mobile and desktop, read the supplied judging rubric, and publish their
critiques and grades at https://farmtact.fly.dev/review.

## Rubric and review method

The supplied GitHub PDF was retrieved as blob
`b5a05dc8e0b849d9f8b1566cbd865151984a1730`. Only its judging-rubric page 13 is used.
The exact extracted rubric is retained in `reports/panel/judging-rubric.txt`.
Other deployment/platform instructions were excluded. It gives seven criteria
and no scoring scale or weights. Reviewer scores use a disclosed unofficial
0–5 evidence scale, with untested criteria left null. Usability /10 is separate.

Ten real Codex specialist agents, review01–review10, were created under the
requested gpt-5.6-sol configuration and at most three specialists concurrently.
They independently choose bounded UI journeys and own separate reports, scripts
and screenshots. Personas are AI simulations, not actual farmers, official
judges or a human user study. All review pages disclose this. Source/test review
is distinguished from browser observations and physical hardware was not tested.

The initial new-session quota was reached after repeated reviewer browser
launches. It was not weakened or reset. Remaining reviewers received legitimate
previously authenticated demo sessions, with returning-session limitations
recorded. Initial blocked attempts were retained; they do not replace actual
mobile and desktop journeys.

## Mobile behavior

Default touch gestures scroll the document. Selecting Move farm explicitly enables
single-finger map dragging. No long press is required; dragging can start on beds,
advisors or empty ground. An eight-pixel movement threshold distinguishes a tap
from dragging. Pointer capture starts only after that threshold; drag-generated
clicks are suppressed while later deliberate taps remain usable. Cancelled and
lost-capture gestures clear their active state. Position is bounded to the farm.

Map arrows, keyboard arrows/Home, recenter and zoom buttons offer alternatives.
A Done button remains within the map as well as the explicit mode toggle above it.
Mouse-wheel scrolling is no longer captured. Native pinch zoom remains available.
Previous/next date buttons and a taller range input reduce reliance on fine
sliders; map labels and icon touch targets were enlarged.

`tests/browser/mobile_navigation.mjs` uses actual CDP touch events at 360/390/430
and mouse/keyboard at 1280. It checks scrolling, drag-from-bed, click suppression,
subsequent taps, cancellation, arrow and keyboard controls, date buttons and
horizontal overflow. Chromium emulation is not physical iOS/Android coverage.

## Public page and publication boundaries

The public /review entry point renders independently of the farm app and never
bootstraps a tenant or loads private farm records. `/api/v1/reviews` serves only a
curated release artifact. `scripts/build_review_panel.py` requires ten reports,
all seven real rubric criteria, valid scores and evidence references, and actual
mobile and desktop screenshots. It copies only explicit owned PNGs to the public
static evidence directory, strips private/unknown fields and rejects credential
patterns. It never publishes raw cookie state, browser storage, API dumps or
arbitrary filesystem paths.

The page includes role, severity and text filters; criterion means exclude null
scores and display their denominator. Evidence links open their galleries. Each
review retains build identity, strengths, critique, next improvements, journeys
and limitations. Candidate retests and changes during review are separate from
original findings. These grades do not prove real farm performance.

Static screenshot requests follow the same admission class as existing artwork,
so legitimate evidence galleries do not consume the unknown-path probe limit.
A regression verifies that unknown probes still reach their original 30/minute
limit. Session, API and inference limits remain unchanged.

## Verification and release

Implementation milestones: mobile browser 54 checks passed; public page draft
with three real reviews 45 checks passed; 102 focused API/deployment/abuse/provider
checks passed before the final static-gallery admission refinement, followed by
34 panel/admission checks passing after it. Final ten-review and live verification
are recorded below when completed. Intermediate failures were repaired or retained
as candid review limitations; no unavailable check is claimed as a pass.

Final local candidate: ten reports, 94 evidence references and 68 explicit PNGs;
58 navigation checks and 93 public-page checks passed at 360/390/430/1280.
The production build, generated contracts and 28 panel/security tests passed.
Reviewer02's independent candidate retest used mouse pointer drags even in a
mobile viewport; its zero page-scroll result is explicitly not native-touch
evidence. Its text-selection observation prompted a map-wide selection/native
drag fix, verified by the final navigation suite. Original findings remain.

Key open product critiques include explaining policy selection and delivery
shortfalls, connecting buyer commitments to allocations, making margin arithmetic
inspectable, and retaining the question-to-result thread in long scenario sheets.
Publishing the panel does not claim these broader findings have been fixed.

Final release: `registry.fly.io/farmtact:deployment-01M22EM68AXASMMMMZB6V715BR`,
existing machine `d8d2060c074438` and persistent volume. The deployed web assets
are `index-DAz3InUb.js` and `index-Bhh55Ty0.css`.

- `reports/mobile_navigation_live.json`: 58 checks passed.
- `reports/public_reviews_live.json`: 93 checks passed, including all 68 public
  evidence images, anonymous access, filters, score means and no inference or
  farm-session bootstrap while browsing the public page.
- `reports/mobile_review_release_preservation.json`: pre-existing farm, recorded
  run, branch result, conversation and quest progress preserved.
- `reports/mobile_review_hosting.json`: Fly application/health passed; Sprite
  web registration removed and port 8080 closed; development PostgreSQL retained.

Public review URL: https://farmtact.fly.dev/review. No physical-device test or
real-farm outcome validation is claimed.
