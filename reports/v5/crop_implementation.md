# V5 crop-art implementation report

Implemented: 2026-09-09  
Scope: all crop SVGs in `apps/web/public/art/crops/`  
Reference contract: `docs/research/v5_crop_visual_brief.md`

Revision: independent compact-size review identified morphology problems in the
first mustard, kale and pak choi candidates. Those forms were revised on the same
date and the review sheet was regenerated from the production paths.

## Outcome

All 18 production crop assets were redrawn as original, repository-native SVGs while preserving the existing filenames:

- Ten harvest-ready catalogue crops.
- Seedling, growing and ready states for caixin, pak choi, kailan and lettuce.

No source photograph, traced shape, embedded raster, remote resource, script, font, biological recipe or application contract was introduced. The source images documented in the research brief served only as visual references for growth habit, leaf shape, petiole/stem mass, foliage edge and surface character.

## Implemented recognition system

| Crop | Primary silhouette | Secondary cue |
|---|---|---|
| Caixin | Slender, airy branching shoot | Small yellow flower/bud cluster appears only when ready |
| Pak choi | Low basal fan | Broad cream-white petioles and smooth dark leaf paddles |
| Kailan | Tall, thick central stem | Sparse blue-green waxy leaves and compact green buds |
| Lettuce | Low concentric cup | Soft overlapping lime leaves and pale open heart |
| Bayam | Three-stem erect cluster | Pointed green/burgundy leaves and terminal spike |
| Kangkong | Ground-running horizontal stem | Arrow-like leaves, visible nodes and pale open stem end |
| Curly kale | Erect crown of individual leaves | Frilled leaf edges, visible midribs and blue-green tone |
| Mustard greens | Open fountain of oversized leaves | Strong pale veins and irregular saw-tooth margins |
| Malabar spinach | Vertical trellised vine | Fleshy heart leaves, magenta stem and dark berries |
| Sweet-potato shoots | Low horizontal runner | Broad palmate/lobed leaves and purple-green vine |

The four simulated crops now progress through shape and mass rather than uniform scaling:

- Caixin grows from a narrow two-leaf shoot into an open branch, then gains a flowering cue.
- Pak choi widens from two pale petioles into a compact petiole fan.
- Kailan thickens its central axis while retaining a sparse upright canopy, then gains green buds.
- Lettuce adds overlapping radial leaf layers to form a low harvest-ready cup.

Seedlings remain stylised gameplay identifiers and are not presented as a botanical diagnostic key.

## Review artifacts

- `reports/v5/crop-art-review-sheet.html` loads the production SVGs directly. It contains ten ready forms at 64 px, ten grayscale forms at 54 px, and the twelve simulated stage assets at 64 px.
- `reports/v5/crop-art-review-sheet.png` is a Chromium rendering of that standalone sheet at 1040 × 1400. It contains no downloaded source imagery.

Visual inspection of the rendered sheet confirmed:

- All ten mature silhouettes remain distinguishable at 64 px.
- The principal cues remain visible in grayscale at 54 px, so colour is supplementary.
- Kale no longer uses rounded cloud/floret clusters that resemble broccoli.
- Bayam no longer reuses the caixin single-tree silhouette.
- Kangkong, Malabar spinach and sweet-potato shoots use three distinct spatial habits and leaf shapes.
- The four simulated stage sequences increase in canopy size/complexity and retain their crop-specific grammar.
- No crop or stage was clipped by its 140 × 120 view box.

## Independent-review revisions

- **Mustard greens:** replaced four deeply notched, angular panels with three
  oversized continuous blades. The new margins use shallow, uneven serrations;
  petiole lengths vary; broad midribs, paired secondary veins and translucent
  fold shapes carry the surface at 64 px without generic noise.
- **Curly kale:** replaced the four-blade symmetric fan with six separately
  outlined, overlapping leaves. Each has its own midrib, irregular curled-lobe
  rhythm and restrained fold patch. Three outer tips and multiple midrib routes
  remain visible in the 54 px grayscale rendering.
- **Pak choi:** shortened the exposed white rays and rebuilt the foliage as broad,
  rounded spoon paddles. Growing now has a compact four-leaf crown; ready adds a
  fifth overlapping inner leaf, heavier cream petioles and a denser bowl. The
  white lower-third fan remains distinct from lettuce in grayscale.

The regenerated 1040 × 1400 sheet was inspected at its native render. The revised
assets remain unclipped. In its actual 64 px row, pak choi reads as a dark compact
crown over a single pale base; kale reads as a low irregular curled crown rather
than a tall feather; mustard retains broad leaf mass around its serrations. In the
54 px grayscale row, pak choi's white base, kale's dark central crown and mustard's
three pale broad blades remain separate without relying on hue. Pak choi seedling,
growing and ready progress through two, four and five canopy blades with increasing
overlap rather than uniform scaling.

## Verification executed

```text
python -c "import glob,xml.etree.ElementTree as E; fs=glob.glob('apps/web/public/art/crops/*.svg'); [E.parse(f) for f in fs]; print('parsed',len(fs),'SVGs')"
# parsed 18 SVGs

rg --files-without-match 'role="img" aria-label=' apps/web/public/art/crops/*.svg
# no output

rg -n '(https?://(?!www.w3.org)|data:|<script|<image|@import|font-face)' apps/web/public/art/crops/*.svg --pcre2
# no output

./apps/web/node_modules/.bin/playwright screenshot --browser chromium --viewport-size '1040,1400' file:///home/sprite/workspaces/Code2/reports/v5/crop-art-review-sheet.html reports/v5/crop-art-review-sheet.png
# completed
```

Every SVG parsed as XML, carries `role="img"` and an `aria-label`, and contains no remote URL other than the SVG namespace, embedded raster, script, import or font-face rule.

## Limits and next acceptance step

The implementation has been visually reviewed by the implementing specialist at actual compact sizes, including grayscale, but the five-person blind recognition exercise specified in the research brief has not been conducted. Integration review should randomise the ready assets without labels and collect independent confusion counts, especially for caixin/kailan and kangkong/sweet-potato shoots.

The standalone sheet verifies the assets themselves. Root integration still needs to inspect them with the real board overlays at 360, 390, 430 and 1280 px and confirm that edition routing makes the new artwork visible only in the new immutable release.
