# V5 audio and game-UX independent review

Reviewed 2026-09-09 from the nine decoded WAV files, deterministic generator,
`audio.ts`, `AudioControls`, result classifiers in `lib/game.ts`, integration in
`App`, `GamePanels` and `DataExplorer`, and `reports/v5/audio_candidate.json`.
This review performed signal analysis and source/browser-contract inspection. It
did **not** hear the sounds, use physical speakers or headphones, test a young
person or professional grower, or substitute AI judgement for those people.

## Decision

The candidate is a measurable improvement over V2's near-silent mix and is safe
to keep as a release candidate. It should not yet be described as human-validated
for audibility, semantic recognition, age appropriateness or long-session comfort.
Two interaction issues found during review were corrected before this report was
closed: master activation now respects the effects toggle, and partial playback
failure now reads as a channel-specific issue with a direct retry action.

## Independent signal measurements

All assets decode as mono, signed 16-bit PCM at 44.1 kHz. Independent readings
reproduced the author's RMS and peak figures:

| Cue | Duration | RMS dBFS | Peak dBFS | Crest dB | Spectral centroid Hz | 95% energy below Hz |
|---|---:|---:|---:|---:|---:|---:|
| Farm garden loop | 64.00 s | -22.00 | -12.04 | 9.96 | 516 | 784 |
| Navigate | 0.14 s | -18.00 | -7.82 | 10.18 | 591 | 664 |
| Detail | 0.20 s | -18.00 | -7.76 | 10.24 | 745 | 835 |
| Confirm | 0.30 s | -18.00 | -7.31 | 10.69 | 660 | 883 |
| Complete | 0.48 s | -18.00 | -6.27 | 11.73 | 655 | 785 |
| Shortfall | 0.48 s | -18.00 | -10.01 | 7.99 | 414 | 446 |
| Withheld | 0.58 s | -18.00 | -9.68 | 8.32 | 456 | 500 |
| Error | 0.34 s | -18.00 | -7.76 | 10.24 | 312 | 332 |
| Sound test | 0.38 s | -18.00 | -6.01 | 11.99 | 655 | 784 |

At V5 defaults, multiplication by 0.55 gives the loop about -27.19 dBFS RMS;
0.70 gives effects about -21.10 dBFS RMS. This supports the claimed improvement
in electrical signal level and preserves at least 6 dB sample headroom before
browser gain. No sample reaches full scale, every file starts and ends at zero,
and DC offset is below the existing -60 dBFS guard.

No BS.1770/LUFS meter is installed. RMS is not perceived loudness: it does not
model frequency weighting, gating, speaker response, ambient noise, hearing
differences or mobile-device volume. “Audible” here means a materially stronger
digital signal, not proof that a person heard it.

## Meaning and musical continuity

The negative cues have a useful coarse ordering. Error is lowest/darkest at a
312 Hz centroid; shortfall is 414 Hz; withheld is 456 Hz. Complete, confirm and
navigation/detail cues occupy a brighter 591–745 Hz band. Durations and contours
also differ. These measurements support distinguishability, but cannot prove a
listener will learn the intended meaning. Visible result text remains essential.

Complete and sound-test are almost the same triad: their zero-padded magnitude
spectra have cosine similarity **0.983**, with matching 655 Hz centroids. That is
reasonable if sound-test means “your output works,” but it cannot independently
test whether completion is recognizable. The product should name the diagnostic
as a generic test tone, or give it a neutral timbre if users interpret it as a
success event.

The loop boundary has a zero sample-to-sample step, so the numerical click test
passes. After the author's edge-envelope correction, independent remeasurement
puts the first 100 ms at -57.02 dBFS RMS and the last 100 ms at -56.86 dBFS RMS,
an absolute difference of **0.16 dB**. This removes the former full-slot envelope
mismatch while preserving a quiet natural fade at the join. The 64-second phrase
and varying notes reduce obvious repetition compared with a 16-second loop. Only
repeated listening can assess seam perception, musical repetition and fatigue.

## Browser and lifecycle review

Controls are opt-in: no `Audio` object is constructed until direct activation,
active state is not persisted, and every reload begins silent. Preferences are
edition-scoped. Browser evidence records 200 responses, decoded durations, an
advancing playhead, loop state, configured gains, 44 px controls, keyboard slider
operation, hidden-tab pause, reload silence and an explicit retry. The assets use
edition-pinned `/v5/audio/...` URLs.

Lifecycle behavior is otherwise sound: master-off pauses and rewinds effects,
visibility pauses media, visible return restarts opted-in music, pagehide and
edition changes tear down players, repeated result IDs are deduplicated, and cue
throttling prevents rapid stacking. Playing one effect stops the previous effect,
which favors clarity over arcade-style overlap.

Two issues were found and corrected during review:

1. `activateAudio()` previously played `sound-test` even when the saved effects
   preference was off. It now creates the diagnostic only when effects are
   enabled, and the explicit effects-test button is disabled and labelled while
   that channel is off.
2. A partial start previously set `blocked=true` while the collapsed control still
   said “Sound on.” It now reports “Sound issue,” names the failed channel while
   acknowledging the working one, and exposes **Retry enabled sound** without an
   off/on detour. The master remains an honest off control when some audio works.

## Gameplay classification

The application triggers navigation only on room navigation, detail on panel
opening, confirm after a scenario/snapshot is frozen, and terminal outcome cues
after polling reaches a final state. It does not sound date sliders or numerical
previews as elapsed farm time. Stable result IDs suppress polling duplicates.

`runSoundOutcome` maps technical failure/cancellation/stale input to error,
review-withheld/no-feasible-plan to withheld, and checks selected/Balanced/first
strategy shortfall before completion. `scenarioSoundOutcome` similarly gives
NO_FEASIBLE_PLAN priority over shortfall. This is substantially more honest than
mapping worker completion directly to a success chime.

Scenario classification is narrower: it explicitly treats only `failed` as an
error and relies on callers not to invoke it for cancellation or stale terminal
states. If scenario APIs can ever return `cancelled`, `stale_input`, or another
technical terminal status, classify those explicitly and include them in caller
terminal predicates. Unknown terminal statuses should use error/withheld rather
than defaulting to complete.

## Age 12 through professional use

The sound set has no speech, alarms, licensed recordings, social audio, violent
imagery or childish voice treatment. Short cues, conservative peaks, visible
equivalents, separate channel toggles and a silent start are appropriate design
choices across the requested audience. Those facts do not establish subjective
age appropriateness. A release listening panel should include at least one young
teen with a guardian-managed session, adult casual players, and growers using the
interface in realistic ambient noise.

Test at minimum: an iPhone and Android phone speaker, laptop speaker, headphones,
system volume at 25/50/100%, quiet and conversational background noise, reduced
motion, screen reader on/off, and a ten-minute loop exposure. Ask listeners to
identify complete, shortfall, withheld and error without seeing labels, then show
labels and repeat. Record confusion pairs, startle, annoyance, seam detection and
whether audio ever implies that farm time advanced or a plan succeeded when it
did not. Do not claim a pass until these observations exist.

## Verified checks

The independent review reused the decoded browser evidence but did not treat its
PASS label as listening evidence. The existing offline signal tests passed, and
the independent measurements above were calculated directly from the committed
PCM samples. Release acceptance should retain:

- exact nine-file inventory, format and deterministic hashes;
- RMS/peak/DC/start-end and loop-step bounds;
- no media request before activation and reload-silent behavior;
- edition-scoped preferences and edition-pinned asset URLs;
- retry after total and partial failures;
- one correct semantic cue per frozen result, including polling deduplication;
- visible text for every state, because audio is supplementary.
