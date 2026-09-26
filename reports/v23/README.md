# V23: narrated guides and public video repair

V23 is published at https://farmtact.fly.dev/ and `/play` from source
`d368784be5eb111e2380da87488593c1b1c73faf` (tag `farmtact-v23`) and pinned image
`registry.fly.io/farmtact@sha256:532a8143c917f3520dfa7896b36cffe6fd029690aa35a96b0093d24b7bddd029`.
It retains the V22 Council workspace and publishes three narrated recordings with
captions, transcripts, posters and seekable video routing. The 5:21 desktop/mobile
master remains in [output/demo-video](../../output/demo-video/README.md), below 100 MB.
The master and raw production files are excluded from the application build context.

GitHub now has exactly one branch, `main`. All ten removed branch tips were already
ancestors of main: their exact identities are retained in `branch-consolidation.json`.
No unique commits were discarded. Historical edition tags, image pins and data
remain preserved without automatic state migration.

| Verification | Result |
| --- | --- |
| Complete isolated PostgreSQL regression | 820 passed, 1 skipped; initial fixture errors resolved and rerun |
| Frontend production build and generated contracts | Passed; existing JS bundle-size advisory remains (556.07 kB raw, 162.28 kB gzip) |
| Private target guards | 13 passed |
| Local media and demo | 20 passed |
| Exact pinned-image media and demo | 20 passed; all three MP4 hashes match committed files |
| Exact pinned-image workflow | 22 passed; calculation, import, save, result, correction, recovery, rooms and 360/390/430/1280px layouts |
| Shared-state preservation after stage and publication | Nine checks passed at each boundary |
| Public media and demo | 20 passed, including captions, posters, transcript, playback, seeking and fallback behavior |
| Public identity, routes and media bytes | 13 passed; exact V23 source, `/` and `/play`, complete MP4 hashes, HEAD and HTTP 206 ranges; only main on GitHub |

Three initial regression setup errors were caused by the missing local
`farmtact_research_test` fixture database. Creating that isolated database and
rerunning exactly the affected cases resolved them; no application change was
needed. The resulting suite has no remaining failures or errors. Provider
credentials were removed from the regression process. Staged and public browser
journeys submitted zero provider requests. All farm actions remain synthetic and
actual operations stay disabled. These automated checks do not establish human
usability or new provider answer quality.

JSON evidence is stored alongside this report. The original media-production
verification remains in [the demo report](../demo-video/README.md).

The streaming gateway omits `Content-Length` on HEAD; full-download hashes and
HTTP 206 `Content-Range` verify exact media size and seekability. A burst of
verification traffic correctly received HTTP 429. The final checksum run passed
after the ordinary cooldown; no limits or counters were reset.
