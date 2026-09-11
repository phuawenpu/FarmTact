# V10 capacity protocol note

The first public V9/V10 overlapping-scenario run completed both jobs in 29.927
and 33.474 seconds, preserved both main farms, rejected cross-edition cookies and
made zero provider calls. Its browse p95 was **6.0815 seconds**, exceeding the
predeclared five-second threshold. Memory available remained above 2,000,000 KiB.
This is a retained failure, not a passing capacity result.

Root started the separate V10 56-day execution trial while those jobs were still
running. That trial also submits numerical planning/replanning work, so the
recorded host workload exceeded the intended pair of overlapping scenario jobs.
This additional load is a protocol deviation and useful evidence of a shared-host
latency limitation; it is not proof that the extra job alone caused every delay.

The [original result](archive/shared-capacity-with-execution-load.json) is retained.
After the execution trial finishes, repeat the original two-scenario protocol with
no other submitted numerical or provider work. Report both outcomes. Do not alter
the five-second threshold, host resources, runtime limits or provider budget.

## Isolated pair result

The repeat also **failed**. Both scenario jobs exceeded the 180-second client
deadline (182.440 and 180.041 seconds); browse p95 was **15.0367 seconds**.
All sampled requests returned successful HTTP statuses, both farms remained
unchanged, cross-edition cookies were rejected and provider usage remained zero.
Available memory remained approximately 1,988,608 KiB after the run.

The repeated failure means the initial overlapping execution workload is not a
sufficient explanation. No root cause is established by these measurements. Do
not claim that ten-edition shared-host capacity passed. Retain both failed runs,
inspect only the two named benchmark jobs, cancel them if still active, and
record their final state in `capacity-cleanup.json`. No additional load test,
resource upgrade, provider call or threshold adjustment follows in this task.

Next acceptance work: measure queue wait versus numerical execution, CPU/steal
and any platform quota effects under repeated sustained load; evaluate a shared
numerical admission limit across editions; enforce/test bounded execution and
cancellation latency; and repeat the fixed latency/terminal deadlines across
multiple prespecified runs. One earlier passing pair is not sustained-capacity
validation.

## Post-deadline state inspection

The scoped inspection found both jobs already `COMPLETED`, so no cancellation or
state mutation was necessary. Their recorded server start-to-completion times
were approximately **236.96 seconds (V9)** and **196.64 seconds (V10)**. They
completed after the client acceptance deadline; the failed latency/deadline
result therefore remains unchanged. See [capacity-cleanup.json](capacity-cleanup.json).
The inspection helper's initial import-path failures occurred before mutation and
are recorded separately.
