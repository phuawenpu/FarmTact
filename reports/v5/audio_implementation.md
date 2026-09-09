# V5 audio implementation

Implementation date: 2026-09-09 UTC

## Result

V5 keeps sound opt-in and starts silent on every visit, while correcting the baseline's
near-silent mix. The controls now explain the silent start, activate with an immediate
test cue when effects are enabled, expose repeatable test/retry actions, preserve separate
music/effect levels, and give the actual range inputs a 44 px interaction height.
Preferences remain edition-scoped and the master active state is deliberately not
persisted. Persisted channel-off choices are respected during activation.

Legacy defaults remain 20% music and 35% effects for v2–v4 compatibility. V5 and later
default to 55% music and 70% effects. This source change is intended for the new immutable
v5 image; it does not redeploy or alter existing edition images or stored preferences.

## Assets and measured mix

`scripts/generate_farm_audio.py` remains the sole deterministic source. It uses Python's
standard library and no recordings, samples, model output, runtime provider or external
licence. Re-running it reproduced all nine checked-in hashes exactly in 16.8 seconds.

The assets are mono signed 16-bit PCM at 44,100 Hz:

| Asset | Duration | File RMS | Sample peak | V5 effective RMS |
|---|---:|---:|---:|---:|
| Garden loop | 64.00 s | -22.00 dBFS | -12.04 dBFS | -27.19 dBFS at 55% |
| Navigate | 0.14 s | -18.00 dBFS | -7.82 dBFS | -21.10 dBFS at 70% |
| Detail | 0.20 s | -18.00 dBFS | -7.76 dBFS | -21.10 dBFS at 70% |
| Confirm | 0.30 s | -18.00 dBFS | -7.31 dBFS | -21.10 dBFS at 70% |
| Complete | 0.48 s | -18.00 dBFS | -6.27 dBFS | -21.10 dBFS at 70% |
| Shortfall | 0.48 s | -18.00 dBFS | -10.01 dBFS | -21.10 dBFS at 70% |
| Withheld | 0.58 s | -18.00 dBFS | -9.68 dBFS | -21.10 dBFS at 70% |
| Error | 0.34 s | -18.00 dBFS | -7.76 dBFS | -21.10 dBFS at 70% |
| Sound test | 0.38 s | -18.00 dBFS | -6.01 dBFS | -21.10 dBFS at 70% |

The old effective levels were -41.33 dBFS RMS for music and roughly -38 to -40 dBFS RMS
for effects. V5 raises them by about 14 dB and 17–19 dB respectively while retaining more
than 6 dB of sample-peak headroom in every file. This is a substantial, measurable
correction without clipping.

The loop grows from 16 to 64 seconds and varies its 32-note phrase, light harmonic layer,
breeze and sparse bird-like oscillators. A Hann-windowed FFT over an inspected loop window
measured a 644 Hz centroid, about 89.1% of energy from 500–1,000 Hz and 8.6% from
200–500 Hz. The old inspected window centred near 279 Hz. The new midrange should survive
small phone speakers more reliably, although only physical-device listening can establish
perceived audibility or quality.

Every file begins and ends at a zero sample. The first loop version had a zero boundary but
its first and last 100 ms measured -52.72 and -82.65 dBFS RMS, a 29.94 dB difference caused
by the final note ending before the file. That was click-free but could create an uneven
phrase gap. The note envelopes now fill their two-second slots: first and last 100 ms are
-57.02 and -56.86 dBFS RMS, a 0.16 dB difference, while the boundary step remains exactly
zero. DC remains below -60 dBFS. This is numerical seam evidence; a listening panel still
needs to judge the musical transition.

## Playback and failure behaviour

`activateAudio()` creates only the enabled channels directly in the user's click call and
waits for their results. If effects were persisted off, master activation does not create,
fetch or play a sound-test element. The explicit effects test is disabled and labelled
**Effects test off** until effects are re-enabled.

A partial failure no longer produces an unusable state: successful audio remains active,
the collapsed master reads **Sound issue**, the detailed status stays visible, one-click
master mute remains available, and **Retry enabled sound** is visible without expanding
preferences. Retry attempts the enabled channels only. If neither can play, the master
returns to inactive. Asset load and effect-play failures expose plain-language status
rather than throwing into gameplay.

The existing guarantees remain:

- no asset object or request before deliberate activation;
- master off pauses music and every effect and resets effect playheads;
- hidden tabs pause all media and opted-in music resumes on visibility;
- page/edition navigation tears down players;
- repeated cues are throttled;
- result cues are deduplicated across polling reports;
- v1 remains silent through its existing caller guards;
- preferences use `farmtact:<edition>:audio:preferences`.

The explicit sound test intentionally does not change music/effects preferences and is
available only when effects are enabled. It uses the configured effects level. A zero
effects slider can therefore produce a silent test; the visible `0%` value explains that
state rather than silently overriding the player.

`sound-test.wav` deliberately uses the same gentle tonal family as `complete.wav` and is
near-identical apart from duration. The diagnostic confirms delivery/output; it is not
evidence that people can distinguish the completion cue. Completion, shortfall, withheld
and error recognition still requires the stated human/device semantic test.

## Semantic API for root integration

Existing calls remain source-compatible. `AudioEffect` adds `shortfall`, `withheld` and
`sound-test`; `playSimulationResult` now accepts `complete | shortfall | withheld | error`.

Root-owned gameplay files should map final evidence, not worker completion alone:

- `complete`: a feasible/accepted numerical result is ready;
- `shortfall`: calculation is inspectable but delivery shortfall or a material constraint
  remains;
- `withheld`: numerical alternatives exist but evidence/council acceptance is withheld;
- `error`: technical failure, cancellation or unavailable calculation.

Call the result API only after the final classification is known. Do not emit `complete`
merely because a worker reached `COMPLETED`, and do not sound slider/date previews as farm
time advancing. Use `confirm` only when assumptions or a snapshot are actually frozen.
Retain visible status text for every cue.

The dedupe key is the supplied result ID. If one record can legitimately move between two
terminal classifications, root should supply a stable versioned event key such as
`<result-id>:<result-version>:<classification>`; otherwise an earlier cue intentionally
prevents a later polling duplicate.

## Verification

Executed locally:

- `python3 scripts/generate_farm_audio.py` followed by SHA-256 verification of all outputs:
  nine deterministic matches.
- `.venv/bin/pytest -q tests/audio/test_v5_audio.py`: **4 passed**. Tests cover exact assets,
  PCM format/duration, RMS, peak headroom, DC/boundary, effective default mix and loop edge.
- `npm run build` in `apps/web`: TypeScript and Vite build passed.
- `node --check tests/browser/v5_audio_candidate.mjs`: syntax passed.
- `FARMTACT_BASE_URL=http://127.0.0.1:8080 FARMTACT_AUDIO_EDITION=v5
  FARMTACT_BROWSER_STATE=/tmp/farmtact-v5-browser-state.json
  FARMTACT_AUDIO_REPORT=reports/v5/audio_candidate.json node
  tests/browser/v5_audio_candidate.mjs`: **22 passed** using the supplied authenticated
  state without creating a session.

The browser run covers silent start, explanations, 55/70 defaults, actual 44 px inputs,
keyboard volume, edition-scoped storage, partial failure and retry, real music/test decode
and advancing play state, effects-off activation, all nine semantic asset decodes,
edition-pinned paths, hidden-tab pause and reload silence. A test-only compiled instance of the actual audio module drove
complete, shortfall, withheld and error fixture events; every event created exactly one
correct player and a repeated polling report created no duplicate. The test bypasses CSP
only to inject that local deterministic harness; production CSP remained unchanged.

The independent AI source, signal and browser review is complete. No physical
speaker/headphone listening was performed, so this report makes no hearing-based audibility,
preference, startle or fatigue claim. A representative phone/device listening panel remains
useful future validation; it is not presented as a newly added release approval gate.
Numerical levels and headless media state cannot substitute for that evidence.
