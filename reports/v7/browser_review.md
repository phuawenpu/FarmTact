# V7 playable council browser review

Date: 10 September 2026 (UTC)

## Result

The final local candidate passed **111 checks with no failures or browser
errors** at 360, 390, 430, and 1280 CSS pixels. Fifteen screenshots were
captured in `apps/web/screenshots/v7-council/` and visually inspected. The
script made 37 research writes, paced more than one second apart. It submitted
no real provider-capable request.

The first-use view has one prominent **Ask council for a plan** action, explains
that the local tool will calculate three options, and keeps the four research
presentation controls collapsed. The full 390-pixel journey followed each
guided next action: calculate, reserve Bed 4, recalculate, mark the additional
order unconfirmed, recalculate, challenge and correct an assumption, compare
the same Balanced policy, and choose a simulation-only version.

The initial-plan measurement was **22.574 seconds**, including an intentional
seven-second wait after the result appeared to replay a stale queued poll. It is
therefore not pure solver latency. The revised calculation measurement was
**15.664 seconds**. The complete automated journey took **71.340 seconds**
because it deliberately paced writes, exercised clarification and checkpoint
recovery, opened evidence, and waited for calculations. The proposed
under-30-second first planning choice remains a human-study hypothesis; these
automation timings neither prove nor disprove first-time usability.

## Interaction findings

- Removable bed context appears beside the composer and can be removed with a
  pointer. An unsupported request produces a bounded clarification. A negated
  reservation does not become a proposal.
- Proposed reservation dates and the protected existing crop are visible before
  application. The apply control is reachable on mobile, and existing work is
  retained.
- A delayed queued response cannot replace a newer completed result. Reloading
  resumes the same chosen v3 research result without another numerical or
  provider POST.
- Checkpoint participation blocks a message with a specific `409`, preserves
  its draft, and allows the message after **Stop discussion**. Evidence opening
  traps focus and closing it returns focus to the invoking control.
- The before/after comparison retains all six Balanced metrics and at least one
  nonzero numerical delta. Choosing it remains explicitly simulation-only and
  does not change the main farm.
- An intercepted unsupported-advisor fixture shows its terminal status, frozen
  reference, validation label, numerical reference, and the warning that it
  cannot authorize a change. This verifies UI handling only; actual calls were
  zero.

## Concept comparison

From a professional planning perspective, the inline council best supports
tracing a constraint into its numerical consequence on desktop because context,
discussion, and deltas remain together. The council sheet gives the clearest
conversation emphasis at narrow widths while retaining selected context. The
adviser cards make speakers easy to scan but create the longest mobile reading
path between discussion and the policy comparison.

All three concepts stayed within the exact requested viewport widths. Direct
geometry and pointer checks found no remaining overlap between farm context and
council controls. The optional open research-control grid fits at 360 pixels,
although long selected option labels truncate; the controls are collapsed in
the default first-use path and remain operable.

## Reproduction and limits

```text
FARMTACT_BASE_URL=http://127.0.0.1:8080 \
FARMTACT_BROWSER_STORAGE_STATE=/tmp/farmtact-v7-numerics-storage.json \
node tests/browser/v7_council_research.mjs

111 checks, 0 failures, 0 errors, 15 screenshots
```

The harness accepts an authenticated storage-state path, uses same-origin page
fetches for main-farm comparison, and can be reused against the public edition
with one separately supplied public test workspace. It was not run against the
public edition during this review.

Headless Chromium does not establish physical keyboard occlusion, device
dictation, screen-reader behavior, touch accuracy on hardware, comprehension,
completion time, or enjoyment by people. The concept observations are an AI
professional-planning review, not participant findings. Earlier failed harness
iterations and their non-product causes are retained in `reports/v7/browser.json`.
