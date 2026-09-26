V23 publication completed on 26 September 2026; [live media checks](../v23/README.md)
confirm the deployed recordings, captions and seeking. Production evidence below
was captured before that release.

# Desktop/mobile walkthrough and guide repair — completed 26 September 2026

Task A: [final walkthrough](../../output/demo-video/farmtact-desktop-mobile-demo.mp4),
321.087 seconds (5:21), 40,937,535 bytes (40.9 MB), H.264/AAC at 2560×1440.
Desktop and mobile follow the same logical workflow, with cursor/tap indicators,
real scrolling and typing, eased desktop close-ups, English synthetic narration,
chapter labels and captions outside the application panels. The exact byte size
and hash are authoritative in [the manifest](../../output/demo-video/media-manifest.json).

Task B: three old silent slide videos are replaced with narrated app footage:

| Guide | Duration | Size |
| --- | ---: | ---: |
| From records to options | 85.17 s | 7.26 MB |
| How the Council earns trust | 79.70 s | 10.06 MB |
| From action to recovery | 85.17 s | 8.51 MB |

Each has a new poster, selectable English WebVTT captions and an exact transcript.
All four MP4s are below 100,000,000 bytes and are committed without Git LFS.
Raw takes, WAVs and intermediate renders remain local and ignored.

## What was broken

All three original MP4s were already tracked. The public latest-edition gateway
omitted `explainers` from its explicit asset allowlist. The three public video
URLs and transcript URL returned 404; see [read-only evidence](public-routing-before.json).
The app itself mounted the directory correctly. The gateway now forwards both
`explainers` and the other missing app-owned `research-evidence` directory, while
retaining named-directory restrictions, origin controls and response headers.
Byte-range requests and 206 responses survive the proxy for video seeking.

The guide UI now handles video/source errors, failed transcript fetches, and
missing or empty transcript entries with clear written fallbacks. Broken media
downloads are not presented as working. The first-use four-scene illustration is
separate from the three prerecorded guides; its controls were checked too.

## Verification actually performed

- Gateway regression: ` .venv/bin/python -m pytest -q tests/editions/test_gateway.py`
  — **18 passed**, including forwarding, HEAD, range seeking, origin/cookie controls
  and rejection of arbitrary file paths.
- Production frontend build and generated web-contract check — **passed**. The
  existing main-bundle size advisory remains; it did not fail the build.
- `node tests/browser/demo_media.mjs` — **20 passed**: pause/resume, next/previous,
  skip, replay, start planning, reduced motion, guidance visibility, all three
  videos loading/playing/seeking, loaded posters and caption cues, exact transcript
  content, download URLs, and injected video/transcript failures. Zero provider
  submissions. [Full result](browser-media-verification.json).
- ` .venv/bin/python scripts/demo_video/verify.py` — **33 passed**: complete audio
  and video decoding of every final MP4, SHA-256, size, fast-start layout, codecs,
  captions, audible nonclipping narration, duration and persisted report/correction
  receipts. Peaks −1.3 to −1.4 dB; mean levels −17.4 to −18.3 dB.
  [Full result](media-verification.json).
- Both real UI sessions completed the logical action sequence without page
  exceptions or provider requests. They used independent local numerical jobs;
  solver allocations can differ. Both saved simulation approvals, short harvest
  reports and revision-2 corrections that retained `recovery_required`.
  [Capture evidence](../../output/demo-video/capture-evidence.json).
- Visual inspection covered [all chapter frames](contact-sheet.jpg) and full-size
  typing close-ups. A real specialist independently reviewed readability and
  narrative truth. A comparison timing mismatch was corrected with a second actual
  UI take; both panes show Balanced at 4 seconds, Resilient at 10, and Balanced at
  16. [Retake evidence](../../output/demo-video/comparison-retake-evidence.json).

The recorded Council question remains an unsent draft; no generated reply is
fabricated. All farm inputs are synthetic and reported results are demonstration
entries, not observations of a real farm. Voice synthesis is local video-production
tooling, not an application provider or speech-input integration.

## Repository and deployment scope

The finished master is saved in `output/demo-video/`, and the three app guides are
in `apps/web/public/explainers/`. Reproduction scripts are in `scripts/demo_video/`.
The source baseline was `6a3ecdf`; routing and UI repairs were pushed in `0730419`,
and the production workflow in `8450c9d`, before the final artifact commit.

This task delivers the repository changes and videos requested by the user. No new
application edition was deployed, and the immutable V22 source/image were not
modified. The live 404s require publication through the existing release workflow;
local playback verification is not a claim of live deployment.
