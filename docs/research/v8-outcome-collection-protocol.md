# V8 authorized real-outcome collection and evaluation protocol

Protocol version: 1.0
Pre-registration date: 11 September 2026
Status: collection and promotion plan only; no real farm outcome data has been supplied

## Purpose and decision boundary

This protocol defines the minimum authorized evidence needed to evaluate demand
and whole-batch crop-cycle models after the synthetic benchmark. It freezes the
target definitions, availability rules, splits, baselines, metrics, and promotion
criteria before real outcomes are examined. The current synthetic models remain
ineligible for production.

Passing this evaluation would permit a time-limited shadow trial that displays
predictions beside existing human practice. It would not permit autonomous farm
actions, equipment control, automatic purchasing, or replacing agronomic review.

## Authorization and governance before collection

The data owner and FarmTact study owner must sign a purpose-limited data agreement
that identifies controller/processor roles, approved farms, permitted fields,
retention, access, incident handling, deletion, publication, and whether any
cross-border transfer occurs. Complete the applicable privacy and research-ethics
review before export. Contractual authorization, rather than technical access,
determines whether a record may enter the study.

Maintain a source register containing dataset ID, owner, authorization record,
collection system, timezone, units, extraction query/version, extractor,
extraction time, row count, and content hash. Reject undeclared files, direct
identifiers, credentials, free-text notes, images, audio, precise personal
locations, health information, and employee-performance fields. Never copy live
source credentials into the evaluation environment.

Use pseudonymous farm and buyer IDs. Store the re-identification mapping with the
data owner outside the analysis dataset. Access is least-privilege and logged;
data is encrypted in transit and at rest. Freeze deletion and backup-expiry dates
before collection. Aggregate published cohorts and suppress cells below five.
Document withdrawals, corrections, and deletions as versioned tombstones so a
prior report can be reproduced without silently retaining withdrawn raw data.

## Required demand and fulfillment records

The unit is an order line at a farm, buyer, crop/SKU, and promised delivery
window. Required fields and semantics are:

| Field | Meaning |
| --- | --- |
| `order_line_id` | Stable pseudonymous line identity; revisions retain lineage. |
| `farm_id`, `buyer_id` | Pseudonymous cohort identities. |
| `crop_id`, `sku`, `grade`, `unit` | Product endpoint and original unit; conversions use a versioned table. |
| `booked_quantity`, `booked_at` | Quantity and event time of the initial commitment. |
| `revision_quantity`, `revised_at`, `revision_available_at` | Each later change and when it became queryable. |
| `cancelled_quantity`, `cancelled_at`, `cancellation_available_at` | Cancellation event and point-in-time availability. |
| `window_start`, `window_end`, `timezone` | Contractual delivery window in local civil time. |
| `delivered_quantity`, `delivered_at`, `outcome_available_at` | Accepted delivered quantity and when the final outcome became queryable. |
| `rejected_quantity`, `substituted_quantity`, `substitute_sku` | Separate outcome components; never folded invisibly into delivery. |
| `stockout_flag`, `capacity_refusal_flag`, `censor_reason` | Whether observed demand or delivery was censored by supply/capacity. |
| `price`, `currency`, `tax_basis`, `price_available_at` | Contract price and availability; missing is distinct from numeric zero. |
| `source_system`, `extract_version` | Provenance for audit and correction. |

The demand target is final net ordered quantity after authorized revisions and
cancellations. Fulfillment is a separate outcome and must not replace latent
demand without the frozen censoring analysis below. Records without a final
outcome-availability timestamp are ineligible as training targets.

## Required crop-cycle records

The unit is a whole biological batch from actual sow through the final harvest or
documented termination. Required fields are farm, facility/zone, batch, crop,
cultivar, recipe/version, production system, occupied area, original units,
planned and actual sow/transplant/harvest events, event availability timestamps,
termination reason, gross harvested mass, rejected mass by declared reason,
fresh marketable mass, grade/pack mass where applicable, measurement method,
scale/device calibration reference, recorder role, correction history, and final
outcome availability.

The primary maturity target is days from actual sow to the first commercial
harvest for a declared single-cut endpoint. The primary mass target is fresh
marketable kilograms per occupied square metre for the complete batch. Gross,
marketable, grade, packed, sold, and waste endpoints remain separate and must
reconcile. Multi-cut crops are excluded until the capability registry's regrowth
contract and persistent-occupancy semantics are implemented.

Do not derive weather, nutrient, disease, or treatment effects from location/date
joins. A future feature must have a documented exposure mapping, units,
availability timestamp, missingness policy, and pre-registered ablation before it
can enter a model.

## Sampling and frozen partitions

Use prospective consecutive eligible records rather than hand-picked successes.
Target at least 52 consecutive weeks, two local seasonal cycles where applicable,
20 farms, 10,000 eligible order lines, and 1,000 complete crop batches. These are
data-adequacy floors, not claims of statistical power; report achieved effective
sample sizes and dependence by farm and buyer.

Before model fitting, a data custodian who is not tuning the candidate assigns:

- **development:** earliest 60% of time within development farms;
- **temporal validation:** next 20% of time within those farms;
- **locked temporal test:** final 20%, unavailable to model authors until the
  candidate, features, and thresholds are signed and hashed; and
- **external-farm test:** all eligible records from at least five separately
  recruited farms absent from development, kept locked until the same point.

Buyer IDs are disjoint where buyer-transfer claims are planned; otherwise report
buyer overlap and do not claim transfer to unseen buyers. No batch, order lineage,
farm, or future revision crosses a disjoint boundary. Every included feature
dependency must have `available_at <= forecast_origin`. The split manifest stores
IDs, date bounds, query hashes, exclusion reasons, and content hashes without
publishing identities.

Forecast origins occur weekly at a frozen local time. Evaluate 1-, 2-, and 4-week
horizons. An order revision enters confirmed demand only after its availability
timestamp. The pipeline must pass a counterfactual leakage probe: permanently
hiding an unavailable outcome and changing its realized value cannot change any
prediction at an earlier origin.

## Missingness, stockouts, and corrections

Publish missingness by farm, field, crop, and time partition before metrics.
Never impute target outcomes across the test boundary. Pre-fit imputers on
development data only and carry missingness indicators. Exclude records only by
the rules in this protocol; report all exclusions.

For demand, the primary analysis includes net ordered quantity and therefore does
not treat low delivered quantity as low demand. A secondary fulfillment model may
use delivery outcomes but must stratify stockout/capacity-censored lines. Run a
sensitivity analysis that (a) excludes censored lines and (b) retains them with
their booked target. Disagreement prevents a fulfillment-benefit claim.

Late corrections receive a new dataset version. If a correction was unavailable
at the historical origin it cannot enter that origin's features, but the final
authorized corrected outcome may be the evaluation target when its lineage and
availability are retained. Freeze and disclose this rule per report.

## Frozen comparators and metrics

Demand comparators are booked-known quantity, last fully available week,
13-week seasonal naive, fixed EWMA alpha 0.35, and an EWMA alpha selected only on
development data. Candidate hyperparameters and features are frozen on temporal
validation. Report MAE, RMSE, WAPE, signed bias, and 80% interval coverage and
mean width for every horizon, overall and by crop. Confidence intervals use a
pre-seeded 2,000-replicate farm-cluster bootstrap.

Crop-cycle comparators are the versioned recipe maturity and marketable-kg/m²
baselines. Report MAE, RMSE, and signed bias for maturity days and marketable
kg/m², plus 80% interval coverage and width. Bootstrap by farm and keep every
batch's measurements together.

Report all metrics on locked temporal and external-farm tests. Also report
farm, crop, production-system, buyer-segment, horizon, and censoring subgroups
with at least 30 independent outcome units; smaller groups are listed as
insufficient rather than pooled selectively. No test-set retuning is allowed.

## Frozen promotion gates

Every required gate must pass on both locked tests:

1. **Authorization and schema:** 100% of included rows have an authorization,
   provenance, unit, target endpoint, and required availability fields; no direct
   identifiers enter the analysis store.
2. **Point-in-time integrity:** zero included dependencies occur after their
   forecast origin; the counterfactual hiding/perturbation probes pass for every
   model and horizon; farm/buyer/batch lineage does not cross a declared disjoint
   split.
3. **Demand primary performance:** at each horizon candidate WAPE is at least 5%
   lower relative to the best frozen non-candidate comparator, and the upper 95%
   farm-cluster bootstrap bound for candidate-minus-comparator WAPE is below zero.
4. **Demand safety:** absolute aggregate bias is at most 5% of mean demand; 80%
   interval coverage is between 75% and 85%; no eligible crop or farm subgroup is
   more than 10% relatively worse in WAPE than its best comparator.
5. **Crop-cycle primary performance:** candidate MAE is at least 5% lower than
   recipe baseline for both maturity and marketable kg/m², with the upper 95%
   cluster-bootstrap bound for each candidate-minus-baseline MAE below zero.
6. **Crop-cycle safety:** absolute bias is at most 1 day and 5% of mean
   marketable kg/m²; 80% interval coverage is between 75% and 85%; no eligible
   crop or farm subgroup is more than 10% relatively worse in MAE.
7. **Robustness:** the stockout sensitivity analyses agree on direction, missing
   target outcomes are at most 5% overall and 10% in every eligible subgroup, and
   performance gates still pass after excluding every single farm in turn.
8. **Operational controls:** model/version rollback, drift alerts, input-schema
   failure, missing-feature fallback, human override, and immutable prediction
   replay pass in an isolated shadow environment.

If no candidate passes, retain the best frozen baseline or no model. A failed
subgroup gate cannot be averaged away. Any threshold, endpoint, feature, split,
or exclusion change creates a new protocol version and requires a newly locked
test period; it cannot repair the current result retrospectively.

## Shadow trial and monitoring after an evaluation pass

A passing candidate runs in shadow for at least eight weeks. Predictions are
timestamped and stored before outcomes, visible as synthetic/research advice, and
cannot mutate plans or equipment. Monitor schema failures, missingness, WAPE,
bias, interval coverage, subgroup degradation, latency, and override reasons.
Predefine alert owners and rollback to the frozen comparator. Promotion beyond
shadow requires separate operational, safety, privacy, and human-factors review.

## Reporting and reproducibility

Publish the signed protocol/version, source and split manifests, code and model
hashes, exact commands, environment lock, every registered metric and gate,
missingness/exclusion flow, deviations, and aggregate privacy-safe results.
Keep raw authorized data private. A report must say `not evaluated` when data or
sample size is absent; synthetic scores and AI reviews cannot fill a real-outcome
gate.
