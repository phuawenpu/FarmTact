# Independent editions and optional audio

The accepted implementation preserves the prior deployed gameplay as v1, with
explicit routing/navigation compatibility adaptations, and creates a fresh v2.
The public root becomes an edition chooser. Each edition owns its image, worker,
PostgreSQL database, volume, cached public observations, cookies and browser
settings. Original source commit: 705b640; original image:
`registry.fly.io/farmtact:deployment-01M22EM68AXASMMMMZB6V715BR`.

Root owns integration and release. Three bounded gpt-5.6-sol specialists built
edition UI, offline original audio, and shared operational controls/publication.
Independent source review and root browser/API tests found and repaired a shared
upstream cookie jar, hidden mobile menu, unversioned art/audio paths, private
control configuration gaps and publication workflow errors. Failed intermediate
checks were not counted as successful verification.

v1 is silent. Later editions have deliberately activated, locally bundled sound
with music/effects controls, per-edition volume preferences, hidden-tab pause,
navigation stop, bounded overlapping effects and completion deduplication.
The original 16-second WAV loop and five cues are reproducible from the included
Python generator; no external asset licence or runtime audio provider is used.
Browser play/error simulation tests are separate from root native-codec playback
verification. Physical iOS/Android hardware has not been tested.

Voice input uses the device keyboard microphone where available, with a hint by
the main message input. FarmTact does not request microphone access or upload
audio. No new provider integration or application inference was needed for these
changes. Historical AI review records retain their own tested builds; release
notes do not claim unresolved farming/business findings were fixed.

Game state is independent while global public abuse counters and the 48-call
daily inference ceiling remain shared. The control database receives only
operational counters; the original game database is retained as a cutover backup
and copied to the separate v1 volume. New editions contain no copied user farms.
Existing anonymous session lifetime rules still apply; editions do not introduce
accounts or cross-device account syncing.

Local verification: API isolation 15 checks; four-width chooser/game/changes/
reviews/native-audio/voice-hint browser journey 41 checks; simulated audio failure
suite 16 checks; broader backend/security milestone 50 tests; subsequent changed
edition/deployment/panel checks 40 tests. Build and generated contracts pass.
Live migration, publication and preservation results are appended after rollout.

Specifications and AGENTS.md record the active-development requirement to push
meaningful progress to GitHub at least every 20 minutes. Progress pushes at
approximately 07:02 and 07:12 UTC preserved the baseline, remote briefing upload,
and edition-control/specification work.


## Live rollout — 9 September 2026

Published chooser https://farmtact.fly.dev/ and independent `/v1/`, `/v2/`.
Both edition applications report source `e9c3edfe10da162e4f50fd5a69df5a4394aa0812`
and use the digest recorded in `config/releases/v1.json` and `v2.json`.
The compatibility image is shared, while immutable edition configuration and
private deployments/databases/volumes are separate. The original source/image
remain recorded separately; v1 is not claimed to be byte-identical old code.

The cutover paused writes after verifying no active jobs. Database restore
matched every game-table count and hash. Cached observations were copied into
each edition's own volume; v2 received no user game data. Original game data
remains on the gateway's retained volume as a recovery backup. Operational
counters moved to the separate control database without resetting usage.

Live verification passed: 21 API isolation/preservation checks, 41 edition
browser checks with native audio playback, 16 simulated audio-state/failure
checks, 58 touch/keyboard navigation checks, and 94 public-review/evidence
checks. All browser suites covered the requested four widths where applicable.
A stale preservation-test assumption compared a full snapshot against a farm
summary; the test now compares the same API representation. Preserved farm,
run, branch, conversation and quest checks all pass. Reports are alongside this
file. These are targeted release checks, not another ten-persona review panel.

All Sprite web/test service registrations were removed, ports 8080–8082 closed,
and PostgreSQL retained. Public Fly chooser and health pass hosting verification.
Meaningful Git progress was pushed at approximately 07:02, 07:12 and 07:25 UTC;
release manifests, live evidence and final source tags follow in the release push.


The final live worker probe also passed seven checks: a saved v2 dataset runs all
three strategies, the planner forecast equals its saved alpha 0.45 preview, no
inference is invoked, the main farm stays unchanged, repeat submission is
idempotent, and v1 cannot read the v2 result. Final edition/deployment/panel
regression: 40 passing tests. See `live_numerical.json` and
`final_release_checks.xml`.

Reproduce the live suites with `scripts/verify_editions.py`,
`tests/browser/editions.mjs`, `tests/browser/edition_audio.mjs`,
`tests/browser/mobile_navigation.mjs`, and `tests/browser/public_reviews.mjs`.
The API verifier accepts a private legacy state file and produces private
Playwright state for authenticated browser checks. Never commit those files.
Browser reports record the live URL and viewport/evidence details. Run the
backend gate with `.venv/bin/pytest -q tests/editions tests/deployment tests/panel`.
