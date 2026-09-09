# V5 baseline crop-art review

Reviewed: 2026-09-09  
Artifact reviewed: `docs/crop-art-contact-sheet.png` plus all 18 SVG files in `apps/web/public/art/crops/`  
Outcome: redesign recommended for v5; no production art changed in this planning phase

## What is already working

- The full catalogue has an illustration, and the four simulated crops have three stage assets.
- Assets are lightweight, original repository-native SVGs with consistent transparent canvases and accessible names.
- Ready-stage pak choi, lettuce, kangkong, mustard greens, Malabar spinach and sweet-potato shoots already attempt meaningfully different growth habits.
- The set has a calm, age-appropriate palette and remains visually compatible with the FarmTact interface.

## Baseline problems

The largest issue is structural repetition. Caixin, pak choi and kailan share essentially the same two-leaf seedling. Their growing assets share a radial stem with five smooth oval leaves, and caixin/kailan ready states add only tiny bud details. This makes stage and species recognition depend on labels and hue.

Several mature assets encode traits too symbolically. Kale resembles a broccoli crown because its leaf mass is built from rounded cloud clusters. Bayam repeats the caixin tree silhouette rather than reading as a clustered young amaranth crop. Mustard has the right serrated idea, but leaf blades and veins are too geometric. The three vine crops are directionally distinct, although their purple/green palettes and sparse leaf counts still create avoidable overlap.

The visual language is clean but very flat. Leaves often use one capsule shape, one centre gradient and no crop-specific venation, edge rhythm, fold, waxiness or fleshiness. The result is consistent but does not reward looking closely, which weakens both the crop-learning value and the pleasure of repeated play.

## Evidence inspected

- NParks [Growing Five Leafy Vegetables](https://www.nparks.gov.sg/publications-resources/articles/growing-five-leafy-vegetables), including its credited source photographs for kailan, Chinese mustard, caixin, kangkong and xiao bai cai.
- GardeningSG: [Bayam](https://gardeningsg.nparks.gov.sg/gardening-resource-library/bayam/), [Kang Kong](https://gardeningsg.nparks.gov.sg/gardening-resource-library/kang-kong/), [Ceylon Spinach](https://gardeningsg.nparks.gov.sg/gardening-resource-library/ceylon-spinach/) and [Sweet Potato](https://gardeningsg.nparks.gov.sg/gardening-resource-library/sweet-potato/).
- NC State Extension: [curly-kale representative](https://plants.ces.ncsu.edu/plants/brassica-oleracea-kale-group/) and [lettuce representative forms](https://plants.ces.ncsu.edu/plants/lactuca-sativa/).
- Repository boundaries in `research/crop_catalogue.json` and `docs/crop-art-provenance.md`.

External imagery was viewed only for reference and is not stored in this review. No source photo is approved for reuse, and no visual observation here changes the crop catalogue's cultivar/taxonomy status.

## Priority findings

| Priority | Finding | Acceptance signal |
|---|---|---|
| P0 | Simulated crop identity collapses in early stages | Caixin, pak choi, kailan and lettuce have different silhouette grammars by growing stage at 54–64 px. |
| P0 | Caixin and kailan remain too similar at ready stage | Thin flowering-shoot bouquet and thick waxy bud-stem read correctly in grayscale. |
| P1 | Kale reads as broccoli | Individual frilled leaves and central midribs replace cloud/floret clusters. |
| P1 | Bayam reads as another branch-form brassica | A clustered, pointed-leaf red/green amaranth habit is evident before colour. |
| P1 | Vine distinctions rely too much on layout/colour | Arrow-leaf hollow-node kangkong, lobed ground-running sweet potato, and heart-leaf trellised Malabar remain distinct in grayscale. |
| P2 | Surface character is generic | Vein, edge and fill texture reinforce each crop without reducing clarity at 54 px. |

## Review decision

Proceed to original SVG implementation using `docs/research/v5_crop_visual_brief.md` as the recognition contract. Treat morphology as visual grounding, not diagnostic evidence. Require actual-size and grayscale recognition sheets before declaring the redesign complete. The screenshots directory `apps/web/screenshots/v5-crop-review/` is reserved for implementation-stage generated contact sheets and in-app evidence; it is intentionally empty at baseline so copyrighted web reference photography is not copied into the repository.

