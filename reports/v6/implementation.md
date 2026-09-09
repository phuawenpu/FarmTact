# V6 shared hosting and crop expansion

Status: exact-image candidate verified; production transfer is next.

The new atlas adds garlic chives (Allium tuberosum) and sawtooth coriander
(Eryngium foetidum), original mature SVG illustrations, local NParks background,
four primary research papers, safe alias boundaries and cautious trade mappings.
All ten prior profiles and the four synthetic farm recipes remain unchanged.
Knowledge profiles do not pretend to be locally validated commercial recipes.

Candidate source: f4606222af6658986b491250de66cb12f6422f32.
Candidate image: registry.fly.io/farmtact@sha256:2415d2a861c83dfda71e13fb25c3187d3082c2f49a987ef3e68751208f63d334.
The image was built from an isolated exact Git worktree, not a moving workspace.

Verification: full backend 458 passed; later deployment/publisher focused tests
29 passed and operator-boundary tests 4 passed. Crop browser checks pass 45/45
both locally and against the exact Fly image, at 360/390/430/1280, with keyboard,
reduced motion, profile-only controls, aliases and evidence links. Visual review
is AI/browser evidence, not a human recognition study or physical-device test.

The shared host uses the exact registered images in separate Pilot containers.
Each keeps its own PostgreSQL cluster, public cache, worker and game state. A
root deployment adapter binds only the fixed edition subtree onto /data, hides
the shared parent, and starts the original unprivileged image entrypoint. The
protected release registry is seeded only when missing and remains unchanged
until publication atomically appends the next healthy edition. Subsequent
publish_edition.py runs reuse this host via config/hosting/shared.json.

Private 4-shared-vCPU/4-GB capacity: initial six-service baseline completed one
isolated and two overlapping numerical jobs; normal reads had p95 0.3631s.
With gateway plus v1-v6, two fresh overlapping jobs completed in 10.069s and
10.073s; reads had p95 0.1674s. All policies were feasible, main farms unchanged,
cross-edition cookies rejected, and inference calls zero. Available memory stayed
above 2.58 GiB. A prior idempotent replay is separately recorded and excluded.
A small additional private IPv6 relay was present during these measurements;
it hides storage, drops privileges and is excluded from production configuration.
These are bounded low-concurrency measurements, not a broad load certification.

Migration verifies every public-schema table's rows/owners, database metadata and
ACLs, source/edition identity and cached file hashes. The user requests deletion
of superseded FarmTact Machines and volumes after verification, leaving one
shared Machine and one volume. Unrelated Fly resources are outside the allowlist.
Temporary protected operator backups remain outside HTTP and the repository.
