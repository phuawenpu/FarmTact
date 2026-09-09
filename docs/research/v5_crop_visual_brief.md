# V5 crop visual-recognition brief

Reviewed: 2026-09-09  
Scope: ten catalogue crops, with seedling/growing/ready stages for the four simulated crops  
Status: implementation brief; no production art changed

## Evidence and use boundary

This brief combines two kinds of statements that must stay distinguishable:

- **Horticultural fact** describes a trait reported or pictured by a cited plant source. It does not resolve an uncertain cultivar, SKU or taxon in `research/crop_catalogue.json`.
- **Art direction** is a proposed visual exaggeration for recognition at FarmTact's 54–64 px gameplay size. It is an interface choice, not a botanical measurement.

Source photographs were inspected as visual references. They are not traced, copied, embedded, redistributed or treated as licensed production assets. V5 artwork should remain original repository-native vector work. Photo credits and reuse terms remain with each source page.

The strongest local reference is NParks' [Growing Five Leafy Vegetables](https://www.nparks.gov.sg/publications-resources/articles/growing-five-leafy-vegetables), which includes credited photographs of kailan, Chinese mustard, caixin, kangkong and xiao bai cai. GardeningSG provides dedicated references for [bayam](https://gardeningsg.nparks.gov.sg/gardening-resource-library/bayam/), [kang kong](https://gardeningsg.nparks.gov.sg/gardening-resource-library/kang-kong/), [Ceylon spinach](https://gardeningsg.nparks.gov.sg/gardening-resource-library/ceylon-spinach/) and [sweet potato](https://gardeningsg.nparks.gov.sg/gardening-resource-library/sweet-potato/). For the catalogue's unresolved representative lettuce and curly-kale forms, the North Carolina Extension plant toolbox supplies image-labelled morphology for [lettuce](https://plants.ces.ncsu.edu/plants/lactuca-sativa/) and the [Brassica oleracea Kale Group](https://plants.ces.ncsu.edu/plants/brassica-oleracea-kale-group/). These two references guide representative silhouettes only; they do not close FarmTact's cultivar and taxonomy gaps.

## Recognition matrix

| Crop | Horticultural facts supported by the references | V5 art direction (interpretation) | Recognition cue at 64 px |
|---|---|---|---|
| Caixin | NParks identifies a Parachinensis-group herb with edible leaves and crunchy stems; its cited photograph shows broad, smooth blades on slender petioles. The catalogue includes flowering shoots as a harvested part. | Use a loose, airy bouquet: several slim light-green stems, oval-to-oblong blades, and one small four-petal yellow flower/bud cluster only at ready stage. Avoid a heavy basal rosette. | Yellow flower speck + open branching silhouette. |
| Pak choi / xiao bai cai | NParks reports green- and white-stemmed forms; its photograph shows upright spoon-like blades gathered from a basal crown and conspicuous fleshy petioles. | Commit to the already declared white-petiole representative. Make the cream petioles occupy roughly the lower third of the silhouette and converge into a bowl-like base; use dark, smooth leaf paddles above. | Bright white U-shaped petiole fan. |
| Kailan | NParks describes kailan as an Alboglabra-group herb; the inspected source photograph shows long, thick green stems with firm blue-green leaves. NC Extension's Chinese-kale entry describes thick firm petiolate leaves and a straight, narrowly branching stem. | Use a tall, top-heavy plant with one dominant thick waxy stem, sparse broad blue-green leaves and a compact green bud cluster. Keep it visibly less branched and less yellow-flowered than caixin. | One thick vertical stalk + blue-green discs + green buds. |
| Bayam | GardeningSG identifies `Amaranthus tricolor`, with green, red or mixed varieties, grown as tight young clusters or an erect plant; spaced plants become taller and bushier. | Show a small *cluster* of three erect tender stems rather than one tree. Use pointed ovate leaves with alternating green and burgundy/magenta patches; reserve a narrow terminal flower spike for mature art. | Red-green upright cluster + pointed blades. |
| Kangkong | GardeningSG identifies `Ipomoea aquatica` as a spreading vine/groundcover with hollow floating stems; NParks' photograph shows a dense stand of long, narrow arrow-like leaves. | Draw a low horizontal runner with two obvious nodes, a cut/open stem end suggesting hollowness, and long sagittate leaves. Keep the canopy linear and flowing rather than shrub-like. | Horizontal pale runner + arrowhead leaves. |
| Lettuce | The catalogue leaves product type and cultivar unresolved. NC Extension documents lettuce as a rosette with forms ranging from round to wavy or lobed; FarmTact currently declares a butterhead-like representative. | Keep the representative label explicit. Build a low concentric cup with broad, tender overlapping leaves, pale folded heart and softly waved edges. No exposed woody stem or radial branch lines. | Layered lime-green cup/rose silhouette. |
| Curly kale | NC Extension describes representative kale leaves as large and thick, with curly/frilly, wavy or serrated margins and green to blue-green colour. FarmTact's taxon/cultivar remains unresolved. | Choose one declared curly representative and amplify edge rhythm: long leaves rising independently from a strong central stalk, each with a visible midrib and scalloped/frilled perimeter. Avoid depicting the canopy as broccoli florets. | Blue-green feathered/frilled leaf crown. |
| Mustard greens | NParks identifies Chinese mustard as `Brassica juncea`; the inspected source image has very broad, upright blades with strongly toothed/serrated edges and prominent midribs. The catalogue warns that its red-mustard evidence does not define every SKU. | Use an open fountain of oversized lime-green leaves with irregular saw-tooth margins and strong pale veins. Burgundy may remain a small representative accent, not the primary identifier. | Huge serrated lime blades. |
| Malabar / Ceylon spinach | GardeningSG identifies `Basella alba` as a large scrambling vine, including white- and red-stemmed cultivars, with leaves, stems and purple fruit harvested. | Keep the declared red-stem representative: thick glossy heart-shaped leaves, fleshy magenta vine wrapping a simple trellis, plus two or three dark-purple berries. Reduce trellis visual weight so the vine owns the silhouette. | Magenta climbing S-curve + hearts + berries. |
| Sweet-potato leaves/shoots | GardeningSG identifies `Ipomoea batatas` as a fast-growing groundcover vine whose leaves vary in shape and colour, including green and purple. The product here is leaves/shoots, separate from tubers. | Use a ground-running purple-green vine with long petioles and repeated, clearly palmate/lobed representative leaves. Show no tuber. Separate it from kangkong through broad lobed blades rather than arrow-like blades, and from Malabar spinach through a ground-hugging rather than trellised habit. | Low purple runner + three/five-lobed leaf stars. |

## Four simulated crops across growth stages

The current seedling and growing assets for caixin, pak choi and kailan share the same two-leaf seedling and radial branch construction. V5 should make identity emerge before ready stage without pretending that a generic cotyledon is diagnostic.

| Stage | Shared factual boundary | Caixin treatment | Pak choi treatment | Kailan treatment | Lettuce treatment |
|---|---|---|---|---|---|
| Seedling | Very early cotyledons alone may not reliably identify these crops. The art is a gameplay label, not a diagnostic key. | Narrow, tall hypocotyl; tiny rounded first true leaf. | Low, broad-set cotyledons; first true leaf begins a spoon shape and pale petiole. | Sturdier blue-green first leaf and thicker short stem. | Very low radial pair with a third pale leaf emerging from the centre. |
| Growing | Species/product form should become readable through growth habit and first true leaves. | Airy upright stem with alternating oval leaves; no bloom. | Compact basal fan; visibly widening pale petioles. | One strong upright axis, sparse waxy broad leaves. | Concentric, low overlapping rosette with an open centre. |
| Ready | “Ready” is a visual state only; maturity remains numerical/data-driven. | Loose flowering-shoot bouquet with small yellow cue. | Dense spoon-leaf crown over a heavy white base. | Thick harvest stem, blue-green leaves, tight green buds. | Full layered butterhead-like cup; no branching stem. |

Growth must read through silhouette, leaf count/overlap and relative mass, not simple uniform scaling. Each stage should preserve the crop's key identity cue, while the ready stage gains one additional cue. Stage labels and accessible names remain necessary because seedling certainty is intentionally limited.

## Baseline confusion pairs

1. **Caixin ↔ pak choi ↔ kailan, seedling/growing:** all currently use near-identical stems and oval leaf capsules. Colour is doing too much work. Give pak choi a low basal fan, kailan a single thick axis, and caixin a slender open branch.
2. **Caixin ↔ kailan, ready:** both use the same branching skeleton plus a tiny bud detail. Separate stem mass, leaf colour/spacing and bud colour before adding texture.
3. **Kale ↔ broccoli icon:** the mature kale asset reads as a cluster of rounded florets. Replace clustered cloud shapes with individually traceable frilled leaves and midribs.
4. **Bayam ↔ caixin:** both are currently upright five-leaf branch forms. Make bayam a clustered, red-green pointed-leaf stand; keep caixin a single loose flowering shoot.
5. **Kangkong ↔ sweet-potato shoots:** both are horizontal `Ipomoea` vines, correctly related but weakly separated at small size. Use arrow leaves and visible hollow nodes for kangkong; broad palmate/lobed leaves and purple petioles for sweet potato.
6. **Malabar spinach ↔ sweet-potato shoots:** purple stems link both assets. Trellised vertical heart leaves and berries distinguish Malabar; a ground runner and lobed leaves distinguish sweet potato.
7. **Mustard greens ↔ generic brassica:** the serrations are present but mechanically regular. Enlarge the broad wrinkled blade and asymmetric tooth rhythm; keep its open fountain distinct from pak choi's smooth paddle rosette.
8. **Lettuce ↔ cabbage:** the current concentric head can read as cabbage. Use softer, looser folds, a pale open heart and irregular tender waves rather than a tight spherical shell.

## Art system

Use a warm botanical field-guide style: confident hand-drawn contour, two or three tonal fills per leaf, a few purposeful vein strokes, and restrained stipple/dry-brush texture clipped inside the leaf. Preserve transparent canvases and the existing upper-left light. The crops should feel more authored without adding faces, fantasy anatomy, neon colours or decorative particles.

Silhouette comes first, then growth habit, leaf proportion, stem/petiole mass, edge type, surface texture and colour. One high-information accent per crop is enough. Texture should follow the organ: subtle wax bloom for kailan, broad smooth gloss for pak choi and Malabar spinach, fine crinkle rhythm for kale, stronger vein relief for mustard, and softer folded shading for lettuce. Do not use texture as noise.

Keep presentation angle and crop scale consistent enough to compare stages, but let growth form control the bounding box: vines should be wider, erect crops taller, and rosettes lower. Avoid identical ground arcs and identical five-leaf counts across the set. Maintain a minimum visual stroke near 1.5 CSS px at 64 px display and avoid essential details smaller than about 3 CSS px.

## Export and recognition acceptance tests

### Asset and accessibility checks

- Every expected asset resolves locally: ten `ready` images and seedling/growing images for caixin, pak choi, kailan and lettuce (18 SVGs total).
- SVGs contain no embedded raster data, external URL, remote font, script or source photograph metadata.
- Each has a transparent canvas, useful `viewBox`, unique crop-and-stage accessible name, and no clipped leaf, stem, shadow or focus-visible wrapper.
- Render at 54, 64, 96 and 160 CSS px at 1× and 2× device scale; essential silhouette and identity cues remain visible at 54 px.
- Check light and dark surrounding panels, 200% browser zoom and grayscale. Names remain available; colour is never the only distinction.
- Reduced-motion mode does not animate decorative texture. Any stage transition uses opacity/transform only and leaves a stable final state.

### Blind recognition checks

- Prepare an unlabeled randomized sheet of all ten ready crops at 64 px. At least 8 of 10 should be identified by crop name by each of five reviewers after seeing the labelled crop library once; no confusion pair should recur for more than one reviewer.
- Prepare a second grayscale sheet. Reviewers should distinguish the four simulated ready crops with at least 90% aggregate accuracy and all ten with at least 70%; failure points to a silhouette problem, not a colour adjustment.
- Prepare four unlabeled three-stage strips. Reviewers should assign seedling → growing → ready order for every crop and distinguish crop identity at growing/ready. Seedling misses are recorded rather than “fixed” with false botanical markers.
- At 54 px, ask reviewers to choose between caixin/kailan, pak choi/lettuce, kangkong/sweet potato and kale/mustard. Each pair must score at least 4/5 correct without reading a label.

### Gameplay checks

- On the farm board at 360, 390, 430 and 1280 px, each simulated crop remains recognizable beside quantity/status overlays; overlays do not cover the key cue.
- Crop art, crop name and stage name agree in board tiles, timelines, crop library, modal, scenario result and replay.
- Stage changes follow stored numerical dates/status. Artwork never asserts readiness, disease, quality, yield or stress on its own.
- A crop remains identifiable during the shortest glance path: farm board → select bed → inspect timeline. No interaction depends on hover.
- Historical editions retain their original immutable assets. New artwork appears only in the new numbered edition.

## Implementation sequence

1. Redraw the three mature simulated-crop forms first and test the caixin/pak-choi/kailan confusion triangle at 64 px.
2. Derive growing and seedling stages backwards from each accepted mature silhouette; keep seedling uncertainty explicit.
3. Redraw the six mature almanac crops, prioritising kale, bayam and the three vine confusion pairs.
4. Generate labelled and blind test sheets from the actual production SVGs; do not hand-arrange substitute mockups.
5. Run automated export/security checks and human recognition review before integrating animation or decorative texture.

