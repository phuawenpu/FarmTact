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
