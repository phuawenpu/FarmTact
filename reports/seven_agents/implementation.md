# Seven-agent edition verification

User direction, 9 September 2026: adopt Sumin Lee's seven-agent model and
repurpose the independent critic as Market/community context. Candidate v3 adds
Demand (Ravi), Weather (Hana), Market (Idris), Production (Mei), Supply Chain
(Lina), Profit (Ben), and Planner (Asha). Earlier editions retain their code,
rosters and databases. Automatic numerical/evidence checks remain local code.

Market's read-only adapter validates up to 500 supplied observations, crops,
source IDs/URLs, UTC observation/retrieval times, reuse permission and cutoff.
It counts reported directions without inventing sentiment or demand. Restricted
and unknown-reuse text is redacted. No feed is connected in this release: the
UI exposes zero connected feeds and zero observations. No scraping, background
inference or reaction-driven numerical adjustment is implemented.

Initial checks: 98 focused backend checks and nine mission evidence-gate checks
passed. Production web build and generated-contract verification pass. New
browser journey passes 28 checks at 360/390/430/1280 pixels, including exact
roster, keyboard selection, readable no-feed panel and no browsing inference.
See ../seven_agents_browser.json and the linked screenshots.

A bounded actual DeepSeek trial on the local v3 candidate completed one direct
reply, two invited replies and seven council replies (10 provider requests;
ceiling 16). Planner conclusion and frozen replay passed. Some returned claims
remain marked unsupported; transcript completion is not a claim of unanimous
or fully grounded model output. No new inference ran on replay. See deepseek.json.

Full regression and deployment verification are in progress. These results do
not yet claim a published v3 or physical-device speech/audio verification.

Pre-publication review fixed archived advisor headers on read/replay while new
replies use current roles. The old six-role shared demo is explicitly archived.
Market provenance details now expand rather than crowding mobile dialogue.
Final responsive journey again passed 28 checks; the intercepted conversation
journey passed 58 checks with zero provider requests or browser errors. Repeated
fresh-session browser tests hit the intended admission cap; final tests reuse
an existing authenticated session without changing limits. The initial full
sweep overlapped a frontend rebuild/type generation and had transient asset/type
failures; all affected cases passed after the build, and a serialized full sweep
is running before deployment.

## V3 deployment and follow-up correction

V3 was published from `f8e04999fba5a82dcb1435c7a4c920e004e76607`, image
`sha256:c71c85442f97ca86a466396439947f417c4ea9267c4eb3b0b1f0eeab4f0cefb6`.
Final serialized backend regression: **412 passed**. Live v3 checks: **19 API
checks** and **28 responsive browser checks**. One actual deployed Market reply
completed (11 total provider requests including the local trial); its unsupported
nested citation was correctly flagged. Completion is not evidence that all model
wording was supported. Earlier v1/v2 images and recorded game data stayed unchanged.
Nine validated public-cache artifacts (200 records) were copied to v3's own volume;
no game/session data was copied. Local HTTP services were retired, ports 8080–8083
closed, and PostgreSQL retained.

Manual live screenshot inspection then found an existing voice-hint flex-layout
issue: at 360 pixels the message input was only four pixels wide. Earlier browser
checks did not assert usable field width. The correction wraps the native keyboard
hint onto its own row and gives the message field and send control 44-pixel touch
height. A regression now requires at least 180 pixels of input width and tests draft
entry without submission at all four widths. This is a new immutable v4 release;
v3 remains inspectable. The candidate stylesheet is tested by an explicitly
labelled browser-only CSS override against v3; the live v3 app is never modified.


V4 is now live at https://farmtact.fly.dev/v4/, from source
`f151082` (full source and pinned digest in `config/releases/v4.json`). The
candidate CSS regression passed 36 checks; the final live v4 journey also passed
36 checks at all four widths with no stylesheet interception. Seven live API
checks passed, including the numerical worker, copied public context, and v3/v4
credential/dataset isolation; no extra provider calls were made. V1–V3 registry
entries remained exactly unchanged, and original v1/v2 saved-record hashes were
rechecked. Both local HTTP service registrations remain removed; PostgreSQL remains.

Progress pushes: 14:46, 14:55, v3 publication around 15:00, 15:07, and v4
publication around 15:11 UTC, followed by the final evidence push. The next
user-requested engagement goal will start with planning for v5, rubric alignment,
reviewer coverage, crop art, audio and news/community sources; it is separate from
this completed release. A subsequent user request adds a measured Fly shared-host
cost comparison and conditional consolidation while preserving edition isolation.
