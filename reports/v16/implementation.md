# V16 explanation completion — unpublished

The full V15 rewrite goal remains active. Published V15 (`a5ab2a8`) passed numerical,
workflow and release gates, but the final semantic audit found raw assumption JSON
and a general proposal explanation reused across unrelated mission stages.
V16 corrects the explanation cards while preserving the integrated experience.
V15 remains immutable/public until the new exact image passes acceptance.

Branch: `feature/v16-explanation-completion`. Root owns edition identity, integration,
operator tooling and release. Card-shell specialist owns stage-specific explanations;
parity specialist independently tests all stages at four widths; workflow specialist
makes existing acceptance harnesses explicit-edition aware. No new models or inference.

The earlier 54px passive-scene minimum asserted by a test was an unsupported
interpretation of the reuse specification. The corrected asset test actually renders
and labels assets at its specified 54/64px review sizes. The original failing report
is retained in reports/v15/final-semantics-published-failure.json.

Local explanation acceptance passes: 49 semantic assertions, including labelled
missing/changed GET fixtures, and 97 independent API-checked assertions across
360/390/430/1280px. Final bundle is `index-C4Jepg7l.js`; main JS 240.25 kB /
75.06 kB gzip. Generated contracts and 12 operator/preservation helper tests pass.
Complete real numerical journeys pass 27 checks each at all four widths (108 total),
with zero provider submissions. Private exact-image and
public release gates remain pending. Human usability remains unverified; actual
farm operations remain disabled.

The API/domain trees match V15's isolated PostgreSQL regression (792 passed, one
skipped). This frontend-only follow-up does not claim another backend regression
run. `frontend-build.json` records unchanged backend provenance and measured assets.

`../v15/final-accessibility.json` adds 11 explicit lifecycle/DOM/viewport checks on
the unchanged motion implementation, including a labelled inert-layout fixture
that moves a real recorded event fully offscreen and proves finite settling and
identical retained facts. Screen-reader and physical keyboard tests remain unclaimed.

