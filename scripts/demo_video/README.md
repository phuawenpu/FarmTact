# FarmTact desktop/mobile video production

These tools record the actual application through Playwright. Two independent
synthetic farm sessions use the same UI sequence. Browser APIs are not mocked.
The visible desktop cursor and mobile tap rings are editorial overlays only.
All quantities, mutations and saved task receipts come from the app.

1. Install the application dependencies, Playwright Chromium, FFmpeg (libx264,
   libass), and Pillow. Start the app against an isolated local PostgreSQL database
   using the Sprite service instructions. Never record real user data or credentials.
2. Install `piper-tts==1.8.0` into a separate Python 3.13 production-tools environment.
   Download the `en_US-lessac-high` ONNX voice and matching JSON configuration from
   the [Piper voice repository](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/high).
   Read its [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/high/MODEL_CARD)
   and linked dataset license. Models are not checked into this repository.
3. `PIPER_MODEL=/path/to/en_US-lessac-high.onnx python scripts/demo_video/narrate.py`
   produces the English synthetic narration locally. This is production tooling,
   not an application inference integration. `storyboard.json` is the exact script.
4. Rehearse with `REHEARSAL=1 CAPTURE_DIR=/tmp/farmtact-rehearsal node scripts/demo_video/record.mjs`.
   Inspect screenshots and `timeline.json`. Respect admission waits; do not reset
   limits to force a successful run.
5. `node scripts/demo_video/record.mjs` records the real-time desktop and mobile
   sessions into the ignored `output/demo-video/work/capture/` folder. Default URL
   is `http://127.0.0.1:8080`; override `BASE_URL` only for an authorized isolated app.
6. `.venv/bin/python scripts/demo_video/render.py` creates the captioned side-by-side
   master, chapter timing, size/hash manifest, and three narrated guide excerpts.
   Editorial close-ups preserve both screens; no app content is synthesized.
7. Rebuild the frontend and run `node tests/browser/demo_media.mjs`, plus
   `.venv/bin/python -m pytest -q tests/editions/test_gateway.py`. Review exported
   contact sheets and decode all final MP4s with FFmpeg before committing them.

Final artifacts belong in `output/demo-video/`. Raw takes, WAVs and render
intermediates stay in its ignored `work/` directory. The renderer rejects any
final MP4 at or above 100,000,000 bytes so every committed video fits the user's
limit. Run byte-size checks before `git add`, never commit a too-large file and
try to remove it in a later commit.

Published application editions remain immutable. This repository change does not
replace the deployed V22 source/image; publication follows `docs/deployment/editions.md`.
