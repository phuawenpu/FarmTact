# FarmTact v5 audio and game-sound baseline review

Review date: 2026-09-09 UTC  
Reviewed releases: public immutable `/v2/` and `/v4/`  
Scope: browser delivery, decoding, play state, controls, lifecycle, edition isolation,
signal measurements, game meaning, accessibility and age suitability. This review made
no inference/provider calls and changed no production code.

## Verdict

The reported “v2 sound was not audible” is credible even though the deployed audio path
works. Native Chromium fetched, decoded and entered play state for the music on both v2
and v4, the playhead advanced, the loop and edition-pinned path were correct, and all six
assets decoded. The most likely cause is the combination of deliberately opt-in sound and
an exceptionally low effective signal level. It is especially vulnerable to disappearing
on a phone speaker, at low system volume, or in ordinary room noise.

At full file level the garden loop is only -27.35 dBFS RMS with a -16.18 dBFS sample peak.
The UI then applies 20% linear gain (-13.98 dB), yielding approximately **-41.33 dBFS RMS
and -30.16 dBFS peak** before the operating-system and device volume controls. Effects land
between -38.24 and -40.31 dBFS RMS at their default 35% gain. Those figures explain an
inaudible experience far better than a missing-file or codec theory.

The interface also begins with **Sound off** on every load, by design. A saved preference
does not restore the master active state, so a returning player must opt in again. This is
safe for autoplay policy, but someone expecting remembered “sound on” can reasonably
conclude that audio is broken. FarmTact cannot detect a muted phone, an unavailable output,
or a browser/OS volume setting, and currently gives no audible test or troubleshooting cue.

## Evidence

The reproducible browser evidence is in [audio_browser.json](audio_browser.json). It records
22 passing checks on v2 and 23 on v4. Each edition used one fresh, reusable browser session;
the test did not reset server state or initiate numerical or inference work.

- Before opt-in, no audio was requested. After a deliberate click, the native music element
  reached `readyState=4`, `paused=false`, and advanced to 0.76 s on v2 and 0.82 s on v4.
- The live music, navigate, detail, confirm, complete and error WAVs returned HTTP 200 with
  `audio/x-wav` and decoded in Chromium. Browser decoding reported mono audio and the exact
  16.00, 0.16, 0.22, 0.30, 0.48 and 0.32 second durations.
- Live v2 and v4 assets have identical SHA-256 hashes to the checked-in deterministic files.
  This rules out a v2-only corrupt or missing asset.
- Master off paused all created media. Backgrounding paused playback and returning resumed
  opted-in music. Reload remained silent. Preferences were stored only under the selected
  edition key.
- At 390 px, the master target is 44 px high. Both sliders provide 172 px of horizontal
  travel and respond to arrow keys, but the native range element itself is only 16 px high.
  Its surrounding label is 44 px; physical touch accuracy still needs real-device testing.
- No uncaught page errors occurred. A headless browser can establish data delivery,
  decoding and playback state; it cannot establish that a particular speaker produced an
  audible or pleasant result.

Screenshots capture the expanded mobile controls in v2 and v4 and the collapsed desktop
v4 control. On mobile, expansion is clear and legible but consumes roughly 180 px above the
farm. Keeping it collapsed by default is appropriate; a short inline “Test sound” action
would diagnose output more directly than opening two channel sliders.

## Local signal analysis

Measurements use every signed 16-bit PCM sample from the deterministic checked-in files.
They are sample peak and unweighted RMS, not a substitute for a calibrated BS.1770 loudness
meter or listening panel. Sparse frequency analysis used a Hann-windowed radix-2 FFT. Files
are mono PCM at 22,050 Hz; the browser resampled its decoded buffers to the output context’s
44,100 Hz.

| Asset | Duration | Peak dBFS | File RMS dBFS | RMS after default gain | Spectral centroid | 95% roll-off |
|---|---:|---:|---:|---:|---:|---:|
| Garden loop | 16.00 s | -16.18 | -27.35 | -41.33 | 279 Hz | 330 Hz |
| Navigate | 0.16 s | -20.15 | -30.28 | -39.40 | 458 Hz | 528 Hz |
| Detail | 0.22 s | -19.20 | -29.45 | -38.57 | 591 Hz | 662 Hz |
| Confirm | 0.30 s | -18.38 | -29.76 | -38.88 | 551 Hz | 662 Hz |
| Complete | 0.48 s | -17.40 | -29.12 | -38.24 | 655 Hz | 786 Hz |
| Error | 0.32 s | -21.06 | -31.20 | -40.31 | 294 Hz | 318 Hz |

The loop’s inspected window puts about 20% of spectral energy below 200 Hz and 78% from
200–500 Hz. Its quiet, low-centred character is pleasant on headphones, but much of its
weight is poorly served by small phone speakers. The sparse bird oscillators exist at
1.18–1.57 kHz, yet are too brief and low-gain to establish consistent presence.

The loop boundary is mathematically clean: first-to-last sample discontinuity is zero,
DC offset rounds to zero, and the maximum sample step inspected around its boundary is
0.000061 full scale. All effects also begin and end at zero. No click-producing seam was
found. The musical phrase does become repetitive because it is only sixteen seconds and
uses eight isolated oscillator notes.

## Game-audio and UX review

The present palette is age-appropriate in the narrow sense: it contains no speech,
frightening sound, harsh alarm, licensed content, advertising cue or manipulative casino
reward pattern. Its sine tones are soft enough for a 12-year-old and unobtrusive enough for
a farm professional. “Complete” rises brightly and “error” is lower, which gives a basic
semantic distinction.

The palette is not yet sufficiently informative for play. Navigate, detail and confirm are
similar rising chimes; their meanings are difficult to learn. A generic completion cue can
also imply success when a calculation merely finished with shortfall, infeasibility or
withheld review. The sound must describe the result, not celebrate computation. Continuous
music should never imply that simulation time or a worker is advancing.

Time has special meaning in FarmTact. Moving the plan-preview date currently changes a view;
it does not grow crops, consume stock or create observations. It should get at most a quiet
scrub/tick, not a harvest or “day advanced” sound. A committed scenario or frozen result can
receive a firmer cue. Real waiting for a numerical job should use visible progress and
silence rather than a ticking clock. This keeps real elapsed time, planning dates and
simulated farm time distinct.

Recommended semantic palette:

| Event | Sound character | Guardrail |
|---|---|---|
| Sound test / enabled | One warm two-note sprout cue | Plays only from explicit activation |
| Navigation | Very short, neutral leaf tap | Throttle repeats; do not fire when selecting the already active room |
| Evidence/detail opened | Light paper/seed texture plus one pitch | Same visible state remains sufficient |
| Assumption saved | Firm, dry confirmation | Do not use for slider previews |
| Feasible result ready | Resolved but restrained three-note cue | Say “calculation ready,” not “you won” |
| Shortfall or constraint | Two-part unresolved cue | Distinct from network/system error |
| Infeasible/withheld review | Neutral low-high query cue | Keep alternatives inspectable; avoid punishment sound |
| Technical failure | Brief soft descending cue | Never startling; accompany an actionable text error |

For younger players, consistency matters more than a large sound library. Pair every cue
with visible words and colour-independent iconography. For adult and professional users,
retain one-click silence, separate channel levels and no forced narration. Do not add farm
animal clichés or busy ambience: they would misrepresent this Singapore crop-planning
setting and compete with numerical work.

## Measurable v5 targets

Render new assets at 44.1 or 48 kHz, 16- or 24-bit PCM, mono unless stereo ambience provides
a tested benefit. Measure final assets with a BS.1770-4/EBU R128 tool before release.

- Background loop: **-23 LUFS integrated ±2 LU**, **true peak no higher than -3 dBTP**,
  default software gain **50–60%**. At a 55% default, an asset at -23 LUFS is approximately
  -28.2 LUFS before device volume. Provide at least 45–75 seconds of variation.
- Effects: **-18 LUFS integrated ±2 LU** over the active event, **true peak no higher than
  -3 dBTP**, default gain **65–75%**. Keep error and constraint cues within 2 LU of other
  effects so warnings are distinct without being louder or alarming.
- Mix headroom: when an effect overlaps music, duck music by **4–6 dB**, attack 30–60 ms,
  release 250–450 ms; combined sample/true peak remains at or below -1 dBTP.
- Loop: boundary sample step below **-60 dBFS**, absolute DC below **-60 dBFS**, and no
  audible click in headphones. Use phase-matched endpoints or an equal-power 80–150 ms
  crossfade. The existing loop already passes the numerical seam criteria.
- Interaction latency: effect playback request within **100 ms** of input and audible onset
  within **150 ms** on reference devices. No more than one repeated navigation cue per
  300–450 ms.
- Controls: master, music, effects and sound-test targets at least **44×44 CSS px**. Give
  sliders a 44 px interactive hit area, not only a 16 px native track, and retain arrow-key
  operation and displayed percentages.

These are production targets, not claims that browser volume maps to calibrated SPL. Test at
the lowest common phone volume step and a conversational room-noise condition; never raise
levels based only on laptop headphones.

## Acceptance plan

Automated release gates:

1. With a fresh edition session, verify silence and zero audio requests before explicit
   activation; then verify fetch, MIME, decode, duration, `play()` resolution, advancing
   playhead, loop, software gain and edition-pinned URLs.
2. Verify master/channel mute, keyboard sliders, displayed values, persisted edition-scoped
   preferences, reload silence, tab pause/resume, navigation cleanup, missing-asset recovery
   and no uncaught errors. Test Chrome/Chromium, Safari/WebKit and Firefox where available.
3. Measure BS.1770 integrated/short-term loudness, true peak, DC, duration, spectral balance
   and loop-boundary discontinuity in CI. Fail outside the target bands.
4. Trigger each real game state: navigation, detail, save, feasible result, shortfall,
   infeasible result, withheld review and technical failure. Assert exactly one correct cue
   and confirm replay/polling does not duplicate it. Preview-date movement must not emit a
   committed-time cue.
5. At 360, 390, 430 and 1280 px, verify visible labels, 44 px hit regions, no farm controls
   obscured when expanded, screen-reader names, keyboard operation and reduced-motion
   equivalence. Audio remains optional regardless of reduced-motion preference.

Human/device panel, reported separately from automation:

- At least one younger participant or safeguarding-aware youth UX reviewer, one casual
  adult, one experienced strategy-game audio reviewer, one accessibility reviewer and one
  grower/farm-operations reviewer. Do not represent a simulated persona as a human test.
- Use a representative iPhone/Safari, Android/Chrome, laptop speakers and headphones. Record
  model, browser, OS, system volume step, environment and whether silent mode/Bluetooth was
  active. Test quiet and ordinary conversational-room conditions.
- Ask participants to enable sound without coaching, identify six cue meanings, notice a
  shortfall versus success, mute quickly, and complete a ten-minute planning journey without
  fatigue. Target 100% discovery of the sound control, at least 80% first-try identification
  for result/constraint/error categories, and no startle or “casino-like” rating above 2/5.
- Run a loop-fatigue review for at least 20 minutes and a speech/screen-reader masking check.
  Any physical audibility or preference conclusion must name the tested device and panel;
  this baseline makes no such claim.

## v5 priority

First fix audibility and diagnosis: normalize/remaster the assets, raise sensible defaults,
add an immediate sound-test cue and explain that each visit starts silent. Then split
“calculation complete” from feasible, shortfall, infeasible and technical-error meanings.
Preserve the current clean seam, offline provenance, opt-in activation, channel controls,
edition-scoped storage and lifecycle behavior.
