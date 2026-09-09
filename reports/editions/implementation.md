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
