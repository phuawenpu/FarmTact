# V5 deployed gameplay addendum

- Deployed endpoint: `https://farmtact.fly.dev/v5/`
- Published source: `0f54565`
- Full deployed gameplay journey: 30/30 passed, zero browser errors and zero inference requests (`game_live.json`).
- Delayed snapshot race: 3/3 passed.
- First chained decision-semantics attempt remained active after the command's 30-second output yield; its final output was not retained by that command session.
- The isolated decision-semantics attempt did not reach an assertion: Playwright `page.goto` exceeded its 30-second `networkidle` threshold while other live numerical jobs were active on the shared tenant. This is recorded as a navigation availability observation, not a semantic assertion failure. Further retries were stopped pending the root timing/log investigation.
- After the other shared-tenant jobs completed, one isolated decision-semantics run completed in 3.85 seconds and passed 6/6 checks. It made no provider or numerical submission. The original concurrency observation remains above as evidence.
