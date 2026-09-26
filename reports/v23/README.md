# V23: narrated guides and public video repair

Release candidate for the user-requested Fly publication. V23 retains the V22
workspace and publishes three narrated recordings with captions, transcripts,
posters and seekable video routing. The 5:21 desktop/mobile master is committed
under `output/demo-video/` and excluded from the application build context.

All ten other GitHub branch tips are ancestors of main; their exact identities
are preserved in `branch-consolidation.json`. Removing those branch references
loses no commits. Prior edition tags, pinned images and data remain retained.

Media validation: 71 scoped checks passed in the [production report](../demo-video/README.md).
Frontend production build, generated contracts and 13 staged-target guard checks
passed. Full regression, exact-image acceptance and public verification are pending.
