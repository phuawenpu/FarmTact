# V11 guided-session adversarial review

The adversarial session suite tests state boundaries that ordinary happy-path
journeys do not establish. It uses isolated SQLite stores and the real FastAPI
routes, session persistence, numerical planner, simulation world, cancellation
logic and retention evaluator. Provider execution is replaced or denied locally;
the suite makes no authenticated inference call.

The tested invariants are:

- recorded negative cash produces an explicit conflict and is never converted to
  a nonnegative planning balance;
- a completed harvest that remains in its sanitation occupancy window carries an
  immutable `harvest_recorded` marker and cannot be changed by a later seasonal
  projection;
- cancellation while a numerical calculation is running prevents its late result
  from creating a result version or becoming the selected schedule;
- an idempotent replay returns the original accepted response, while changed input
  under the same key and a stale revision under a new key are rejected;
- retention refuses to delete an expired anonymous tenant while a guided planning
  job is queued; and
- a review denied by the shared daily reservation gate records zero calls and
  never enters the provider workflow, while its numerical strategy remains usable.

These checks establish local contract and persistence behavior. They do not prove
multi-process PostgreSQL scheduling, shared-host capacity, browser usability, or
actual DeepSeek response quality. Those remain separate release acceptance trials.
