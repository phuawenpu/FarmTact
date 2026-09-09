# Crop and advisor art provenance

Last reviewed: 2026-09-08

## Scope and provenance

FarmTact ships original, hand-authored SVG illustrations under `apps/web/public/art/`. The crop art was drawn in the repository from observed plant traits described and pictured by NParks and GardeningSG. No source photograph, tracing, embedded raster image, remote font, or third-party vector is included in the assets. The advisor characters are original fictional adults and do not depict or derive from real people.

All SVGs use a transparent canvas, a consistent front-three-quarter presentation, upper-left lighting, soft ground shadow, restrained colour gradients, and subtle SVG filter texture. They remain legible at the compact 54–64 px placements used by the interface. The texture is deterministic and does not call an image service at runtime.

The external pages and photographs were used as visual references only. Their inclusion here does not assert a licence to redistribute the photographs. NParks photo credits remain on the source pages; FarmTact therefore ships none of those photographs. The original FarmTact vectors follow this repository's project licence or, if the repository has no declared licence, remain covered by the repository owner's default copyright. This record is asset provenance, not a legal interpretation of the source sites' terms.

## Reference pages and selected traits

| Reference | Crops informed | Traits used in the original artwork | Reuse treatment |
|---|---|---|---|
| [NParks: Tips On Growing Brassica Edibles](https://www.nparks.gov.sg/publications-resources/articles/tips-on-growing-barssica-edibles) | caixin, pak choi, kailan | Caixin's slender smooth stems and yellow flowering shoot; pak choi's dark leaves and contrasting broad white petioles; kailan's blue-green leaves and thick pale stems | Page and credited photographs consulted as references; photographs are not copied or distributed |
| [NParks: Growing Five Leafy Vegetables](https://www.nparks.gov.sg/publications-resources/articles/growing-five-leafy-vegetables) | caixin, pak choi, kailan, mustard greens, kangkong | Brassica growth forms; broad mustard leaves; kangkong's creeping habit | Page and credited photographs consulted as references; photographs are not copied or distributed |
| [GardeningSG: Bayam](https://gardeningsg.nparks.gov.sg/gardening-resource-library/bayam/) | bayam | Upright clustered Amaranthus habit; green, red, and mixed foliage forms; tender stems and flower spike | Reference-only; no source photograph shipped |
| [GardeningSG: Kang Kong](https://gardeningsg.nparks.gov.sg/gardening-resource-library/kang-kong/) | kangkong | Sprawling vine, narrow arrow-like leaves, long hollow stems and visible nodes | Reference-only; no source photograph shipped |
| [GardeningSG: Ceylon Spinach](https://gardeningsg.nparks.gov.sg/gardening-resource-library/ceylon-spinach/) | malabar spinach | Trellised climbing habit, thick heart-like leaves, red/white stem cultivar distinction, dark berries | Reference-only; no source photograph shipped |
| [GardeningSG: Sweet Potato](https://gardeningsg.nparks.gov.sg/gardening-resource-library/sweet-potato/) | sweet-potato leaves/shoots | Sprawling vine, lobed/heart-like leaves, green-to-purple foliage variation | Reference-only; no source photograph shipped |

Lettuce and curly kale use widely recognizable representative market forms solely to keep the almanac readable: a green butterhead-like lettuce and a blue-green curly kale. The catalogue currently leaves lettuce product type/cultivar unresolved and blocks kale taxon/cultivar confirmation. The artwork must not be read as resolving those records.

## Crop identity matrix

| Crop ID | Representative illustrated form | Distinguishing visual treatment | Files |
|---|---|---|---|
| `caixin` | Parachinensis-group flowering vegetable | Slim branching stems, oval leaves, small yellow buds | `caixin-{seedling,growing,ready}.svg` |
| `pak_choi` | White-petiole pak choi form | Spoon-shaped dark leaves and broad cream-white petioles in a basal rosette | `pak_choi-{seedling,growing,ready}.svg` |
| `kailan` | Alboglabra-group representative | Upright thick pale stem, waxy blue-green leaves, compact green buds | `kailan-{seedling,growing,ready}.svg` |
| `bayam` | Mixed green/red `Amaranthus tricolor` representative | Upright fine-branched plant, pointed leaves, magenta stem accents and flower spike | `bayam-ready.svg` |
| `kangkong` | `Ipomoea aquatica` representative | Horizontal creeper, long hollow-looking stems, nodes and narrow arrow-like leaves | `kangkong-ready.svg` |
| `lettuce` | Green butterhead-like representative | Low concentric head with softly waved overlapping leaves | `lettuce-{seedling,growing,ready}.svg` |
| `kale` | Curly-leaf kale representative | Deeply ruffled, blue-green leaves around a strong central stalk | `kale-ready.svg` |
| `mustard_greens` | Green/red mustard representative | Broad toothed leaves with burgundy shading and an open upright crown | `mustard_greens-ready.svg` |
| `malabar_spinach` | Red-stemmed `Basella` representative | Magenta twining vines on a trellis, fleshy heart-like leaves and dark berries | `malabar_spinach-ready.svg` |
| `sweet_potato_leaves` | Green/purple leaf-crop representative | Ground-running purple vine and repeated lobed leaves; no tuber is shown | `sweet_potato_leaves-ready.svg` |

The four crops used by the current synthetic numerical model have three hand-authored stages. `seedling` means the visual nursery/early form, `growing` is an intermediate canopy, and `ready` is a visual harvest-ready state. The images do not calculate or certify crop maturity. All six other catalogue crops have mature almanac art only and intentionally resolve to the `ready` asset in `CropArt`.

Cultivar, SKU, production system, taxonomic status, and saleable product specification remain those of `research/crop_catalogue.json`. Each illustration is a representative visual form, not botanical evidence, a farm observation, a diagnosis, or an agronomic recommendation.

## Advisor portraits

The seven portraits share a circular painted treatment and bust scale while retaining recognizable clothing, silhouettes, and work props:

| File | Character cues |
|---|---|
| `advisors/mei.svg` | Production advisor in a light field coat, glasses, seedling sample |
| `advisors/ravi.svg` | Demand advisor in an orange shirt with order clipboard |
| `advisors/hana.svg` | Weather advisor in a blue rain jacket and yellow field cap with anemometer |
| `advisors/ben.svg` | Profit advisor in work shirt, glasses and tool belt |
| `advisors/asha.svg` | Planner in plum blazer with pavilion table diagram |
| `advisors/idris.svg` | Market advisor in slate vest with evidence stack and magnifier |
| `advisors/lina.svg` | Supply Chain advisor with a packing clipboard; original hand-authored SVG added for v3 |

These files are presentation assets. Character expertise, current task, notification state, dialogue, evidence status, and conclusions must come from application data rather than from the illustration.

The original six-portrait contact sheet and PNG document the first artwork release. V3 reuses those portraits with updated role descriptions and adds Lina; older editions retain their original labels. No third-party imagery was used for Lina.
