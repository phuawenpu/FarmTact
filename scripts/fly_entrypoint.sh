#!/bin/sh
set -eu
# The Fly volume arrives root-owned; only prepare fixed runtime directories.
install -d -m 0700 -o farmtact -g farmtact /data/postgres /data/public-data
install -d -m 0700 -o farmtact -g farmtact /tmp/farmtact-pg
exec gosu farmtact python /app/scripts/fly_boot.py
