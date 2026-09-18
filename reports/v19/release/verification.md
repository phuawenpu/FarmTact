# V19 publication verification

V19 was published on 18 September 2026 from source
`ef4cba0e5efa84c8e7f8db9fbb36c831281a19f5` and pinned image
`registry.fly.io/farmtact@sha256:ab798306de8fee61f40ecf0ca0fab5c24359ab9544e32ac258b1cc8f6614027d`.
The public health endpoint returned that exact edition and source; `/` and `/play`
both returned 200. The immutable `farmtact-v19` tag is present on the remote.

Verification passed: Vite production build; 11 transport guards; a nine-check
Council-card browser test; isolated PostgreSQL regression (804 passed, one skipped);
the full local responsive card journey; a 20-check staged operator trial; and the
exact pinned-image staged browser journey. Those browsing and operator checks made
zero provider submissions. The shared-state preservation comparison passed before
staging, after staging and after publication, including retained history, security,
budgets, unexpired abuse counters and stored edition subtrees.

This is automated and operator acceptance evidence. It does not establish
representative-user comprehension or real-farm suitability; actual operations remain
disabled.
