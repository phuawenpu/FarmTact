# FarmTact desktop + mobile walkthrough

[Play or download the narrated walkthrough](farmtact-desktop-mobile-demo.mp4) — **5:21 · 40.9 MB · 1440p**

A desktop browser and mobile web view follow the same real application workflow
side by side. The edit includes a visible cursor/tap indicator, natural scrolling
and typing, focused desktop close-ups, English synthetic narration and captions.
The footage uses two isolated synthetic farm sessions and real local numerical
calculations. There are no mocked app responses or generated Council answers.
The Council question is explicitly shown as an unsent draft.

[English captions (WebVTT)](farmtact-desktop-mobile-demo.vtt) ·
[English captions (SRT)](farmtact-desktop-mobile-demo.srt) ·
[Chapter timing](edit-decision-list.json) · [File sizes and SHA-256](media-manifest.json)

The workflow inspects farm records, calculates and compares plans, drafts a
Council question, changes demand to 105%, recalculates, confirms a simulation
plan, reports a short harvest, saves an auditable correction, inspects recovery,
and opens the crop library and guide collection. No physical operation is enabled.

Three shorter app guides are in
[`apps/web/public/explainers/`](../../apps/web/public/explainers/):

- [From records to options](../../apps/web/public/explainers/observe-decide.mp4)
- [How the Council earns trust](../../apps/web/public/explainers/council-evidence.mp4)
- [From action to recovery](../../apps/web/public/explainers/act-replan.mp4)

The guide MP4s contain narration and use the app's selectable WebVTT captions.
Their posters and matching transcripts are committed beside them. The master
walkthrough has captions in its editorial footer for portable playback.

[Production scripts and reproduction instructions](../../scripts/demo_video/README.md)

Voice: local Piper `en_US-lessac-high` English speech synthesis; original narration
is in `scripts/demo_video/storyboard.json`. No speech service was added to the app.
Raw takes and rendering intermediates remain local in the ignored `work/` folder.
Final videos are committed only when below 100,000,000 bytes each.

Repository fixes include the public gateway's missing guide route and clear video
and transcript error states. This recording is from the updated local checkout;
it is not evidence that a new immutable application edition has been deployed.

Verification: [completed task report](../../reports/demo-video/README.md).

## Chapters

- **0:00** — A delivery question, on two screens
- **0:20** — Read the farm before changing it
- **0:40** — Inspect the source records
- **1:00** — Calculate real planting alternatives
- **1:25** — Compare the tradeoffs
- **1:45** — Draft a focused Council question
- **2:10** — Review an explicit change
- **2:44** — Save a simulation plan deliberately
- **3:04** — Open a task from the approved plan
- **3:24** — Report a short result
- **3:49** — Correct the record without erasing it
- **4:09** — Review future recovery
- **4:29** — Look up the crop behind the plan
- **4:50** — Replay the guides when you need them
- **5:05** — One workflow, desktop and mobile
