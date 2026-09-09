# Independent AI review of v5 crop artwork

Review date: 2026-09-09 UTC  
Reviewer: Codex visual/UX reviewer (AI), independent of the crop-art implementation  
Scope: the 18 production SVGs, labelled colour and grayscale review sheet, and actual
candidate Crop atlas and farm views at 360, 390, 430 and 1280 px. This was not a human
blind-recognition or physical-device study.

## Decision

**Accepted after targeted revision.** The first pass required changes to mustard greens,
curly kale and pak choi. The regenerated production sheet resolves those three morphology
concerns at the reviewed 64 px colour and 54 px grayscale sizes. All ten ready forms and
the four simulated stage sets are suitable for the v5 candidate. Human blind-recognition
testing remains outstanding.

The initial concerns were well founded, with one qualification; the final re-review below
records how they were resolved:

- On the initial sheet, mustard greens read as angular ginkgo leaves, flags or paper cut-outs rather than
  oversized broad mustard blades. This concern is confirmed.
- Initial kale read as a stiff, highly symmetrical feather/palm fan. It no longer looked like
  broccoli florets, but it still lacks a believable mass of independently frilled kale
  leaves. This concern is confirmed.
- Initial pak choi blades were not literally small in the SVG coordinate system, but at gameplay
  size their long splayed petioles make the canopy look sparse and the pointed blades look
  narrower than spoon-shaped pak choi paddles. The concern is confirmed as a proportion and
  silhouette issue rather than simply leaf size.

## Evidence reviewed

The labelled sheet renders all ten ready crops at 64 px, all ten in grayscale at 54 px,
and the four simulated crops in three stages at 64 px. Because names remain visible, it
supports comparative expert review but cannot provide a blind-recognition score. No claim
is made against the brief's five-human-reviewer thresholds.

The candidate atlas was inspected in one existing authenticated session at 360, 390, 430
and 1280 px. Separate screenshots cover the farm at the same widths. No session, provider
call, farm mutation, build or service was created. The assets remained clear and unclipped
in card frames. Mobile cards provide substantially larger artwork than farm beds; the farm
therefore remains the stricter glance-recognition context.

Screenshots are under `apps/web/screenshots/v5-crop-peer/`:

- `atlas-360.png`, `atlas-390.png`, `atlas-430.png`, `atlas-1280.png`
- `farm-360.png`, `farm-390.png`, `farm-430.png`, `farm-1280.png`

## Crop-by-crop findings

| Crop | Recognition and morphology | Grayscale / gameplay | Decision |
|---|---|---|---|
| Caixin | The open branching habit, slim green axis, oval blades and tiny yellow bloom cue match the intended loose flowering shoot. It is visibly airier than kailan and unlike the basal pak choi. | The flower loses colour information in grayscale, but the open branch remains legible. Seedling → growing → ready adds height, branches and bloom rather than uniform scaling. | Pass |
| Pak choi | Revised broad, rounded overlapping paddles now form a compact crown over the strong white converging base. The ready form adds a fifth inner blade and visibly heavier petioles relative to growing. | White base and dense dark crown distinguish it from lettuce in grayscale; growing → ready now adds overlap and inner mass. | Pass after revision |
| Kailan | One thick waxy-looking vertical stalk, sparse blue-green leaves and compact green buds create the clearest successful morphology in the simulated trio. It is top-heavy and much less branched than caixin. | Strong axis and sparse discs survive grayscale and small farm use. All three stages preserve increasing stem mass and identity. | Pass |
| Lettuce | Low concentric layers, lime tonal separation and pale open heart read as a representative tender rosette. The silhouette is looser than a spherical cabbage. | Layer overlap and low cup remain distinct from pak choi without colour. Stages add concentric mass and are easy to order. | Pass; retain representative-form caveat |
| Bayam | Three red-green erect stems and pointed leaves distinguish it from caixin. The magenta shapes can momentarily read as buds, but the clustered habit is clear at atlas size. | In grayscale it still has multiple strong axes and a denser vertical cluster than caixin. At farm size the identity depends more on the label because the red-green distinction compresses. | Pass with minor caveat |
| Kangkong | Low horizontal runner, nodes and repeated sagittate leaves give a strong growth-habit cue. The leaves are aggressively angular, but they remain recognisable as arrow-like rather than palmate. | The horizontal line and nodes survive grayscale. It separates cleanly from the broader sweet-potato stars. | Pass |
| Curly kale | Revised crown contains six independently drawn leaves at varied angles, with continuous midribs, irregular scalloped margins and restrained fold highlights. It reads as curled leaf mass rather than broccoli. | At least three tips and their ribs remain traceable at 54 px grayscale. The overall crown is still compact, but no longer reads as one rigid palm/feather shield. | Pass after revision |
| Mustard greens | Revised form uses three larger continuous broad blades, asymmetric shallow teeth, strong midribs, secondary veins and fold shading. Leaf mass now dominates its shorter three-stem fountain. | Grayscale reads as broad serrated foliage rather than ginkgo, pennants or sweet-potato stars. | Pass after revision |
| Malabar spinach | Vertical magenta S-curves, simple trellis, glossy heart/ovate leaves and purple berries form a memorable, grounded combination. The trellis is light enough that the vine owns the silhouette. | Berries and climbing structure survive grayscale, while the upright habit clearly separates it from sweet potato. | Pass |
| Sweet-potato shoots | Purple ground runner and repeated three-lobed/palmate blades distinguish it from both trellised Malabar and arrow-leaf kangkong. No tuber is implied. | The low runner survives grayscale. Leaves verge on crown/star symbols, but the repeated petiole-and-runner relationship keeps the plant interpretation. | Pass with minor softening opportunity |

## Initial required revisions

### Mustard greens

Replace the four regular polygon-like leaves with fewer, larger blades whose overall mass
is broadly ovate or oblong. Put irregular teeth along a continuous curved margin instead
of alternating deep triangular cut-outs. Introduce mild left/right asymmetry, a broader
midrib, two or three secondary veins and restrained fold/wrinkle shading. Keep the open
fountain, but shorten at least two petioles so leaf mass—not empty stem space—dominates at
54 px.

Acceptance: in grayscale at 54 px it should read as broad serrated foliage before it reads
as ginkgo, arrowhead, pennant or sweet-potato star. Teeth can be exaggerated, but the
underlying blade must remain broad and continuous.

### Curly kale

Break the single symmetrical fan into five or more individually traceable leaves emerging
at varied angles from a central stalk. Each leaf needs a continuous midrib and a curved,
scalloped/frilled perimeter with different lobe rhythm on each side. Add small overlapping
fold shadows or alternating edge tones; avoid four blades sharing one outer shield shape.

Acceptance: the grayscale silhouette should look like a loose crown of curled leaves, not
a palm frond, feather, artichoke, shield or broccoli floret cluster. At 64 px, at least
three separate leaf tips and their midribs should remain traceable.

### Pak choi

Keep the excellent white basal cue. Shorten the apparent exposed petiole length, widen and
round the blades into smooth spoon paddles, and overlap the inner two leaves so the mature
plant forms a denser bowl/crown. Let cream petioles occupy roughly the lower third, rather
than visually separating leaf blades across most of the height. Ready should gain an inner
leaf or visibly heavier overlapping crown compared with growing.

Acceptance: at 54 px the plant should read as a compact dark paddle crown over one fleshy
white U-shaped base, rather than four green petals on pale rays. Grayscale must remain
distinct from lettuce through the exposed white petiole fan.

## Final targeted re-review

The crop specialist regenerated the review sheet from the revised production SVGs. This
second AI pass examined the three changed forms in colour at 64 px, grayscale at 54 px and,
for pak choi, growing and ready side by side.

- **Mustard accepted.** Three broad continuous leaf bodies now carry irregular shallow
  teeth rather than deep mechanical triangular cut-outs. Curved mass, asymmetric margins,
  midribs, secondary veins and fold tones remain visible at review size. The former
  ginkgo/pennant reading is no longer the dominant silhouette.
- **Kale accepted.** Six leaves can be traced through separate tips and midribs. Their
  varied directions, scalloped edges and overlapping fold tones break the former rigid
  four-blade symmetry. At 54 px the crown remains compact and somewhat triangular, but it
  reads as layered curled foliage rather than a single palm feather or broccoli head.
- **Pak choi accepted.** Growing and ready now use wide rounded paddles with substantial
  overlap over a compact white base. Ready adds a central inner blade and heavier petiole
  mass, so it is not merely a scaled four-ray growing plant. In grayscale its exposed white
  base remains clearly separate from lettuce's layered lime cup.

These acceptances are expert visual judgments from actual generated assets. They do not
claim that unprompted users will name each crop correctly.

## Artistic system and texture

The set is coherent: warm ground shadows, confident dark contours, restrained gradients
and consistent upper-left lighting make it feel authored. Silhouette differentiation is
substantially stronger than a shared generic five-leaf plant. The vines, rosettes and erect
crops now occupy appropriately different horizontal/vertical envelopes.

Texture remains deliberately restrained. The revised kale now has crop-specific edge/fold
rhythm and the revised mustard has useful vein/fold relief; lettuce benefits from layered
tonal folds while pak choi appropriately stays smoother. The broader set still relies on
gradients and purposeful vein strokes rather than stipple or dry-brush texture, which is a
reasonable tradeoff at 54 px. Do not add uniform noise to every crop.

Distinctive colour is helpful without being the sole discriminator in most pairs. The
grayscale sheet supports separation through habit for pak choi/lettuce,
kangkong/sweet-potato and Malabar/sweet-potato. Caixin/bayam becomes less immediate but
retains one-stem-open versus multi-stem-cluster structure. Kale's compact scalloped crown
and mustard's open three-blade fountain now use visibly different edge and growth language.

## Stage and game usability

All four simulated crops show stage progression through silhouette, leaf count, overlap
and mass. Pak choi seedling is low and broad-set; growing establishes four overlapping
paddles; ready adds a fifth inner blade and heavier white base.

On the Crop atlas, every asset is large, named and easy to compare at all four widths. On
the farm, bed labels do not cover the crop itself and interaction does not depend on hover.
At narrow widths, the board art is small enough that labels remain essential—as the brief
correctly requires. Caixin, kailan, pak choi and lettuce are separated by branch, stalk,
white base and rosette respectively. The revised pak choi improves the quickest glance path.

The artwork appropriately makes no visual claim about disease, measured yield, quality or
stress. Ready-state images remain presentation cues; numerical dates and text must remain
authoritative.

## Remaining release validation

The production sheet and expert re-review are complete. The brief's randomized, unlabeled
human recognition protocol remains necessary; this labelled AI review cannot replace it.
Prioritise these pair checks at 54 px in both colour and
grayscale:

1. pak choi versus lettuce;
2. kale versus mustard;
3. mustard versus sweet-potato shoots;
4. caixin versus kailan.

The human result should record each answer rather than report only an aggregate. Keep the
brief's target of 4/5 correct per confusion pair and document recurring wrong labels. Also
verify the revised farm at 360, 390 and 430 px, since passing the larger atlas alone does
not establish playability.
