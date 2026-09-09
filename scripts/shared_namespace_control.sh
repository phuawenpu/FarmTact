#!/bin/sh
# Fixed operator-only ancestor-PID-namespace pause for the six migrated services.
# No environment reads; identity is derived from exact cmdline, NSpid and mount.
set -eu
umask 077
record=/run/farmtact-v6-namespace-freeze
operation=${1:?STOP or CONT required}
case "$operation" in STOP|CONT) ;; *) exit 40;; esac
validate() {
  name=$1 pid=$2 started=$3 namespace=$4
  test "$(awk '{print $22}' /proc/$pid/stat)" = "$started"
  test "$(readlink /proc/$pid/ns/pid)" = "$namespace"
  test "$(awk '$5=="/data" {print $4}' /proc/$pid/mountinfo)" = "/$name"
  tr '\000' '\n' < /proc/$pid/cmdline | grep -qx '/app/scripts/fly_boot.py'
  awk '$1=="NSpid:" && NF>2 && $NF==1 {found=1} END {exit !found}' /proc/$pid/status
}
if [ "$operation" = STOP ] && [ ! -f "$record" ]; then
  (set -C; : > "$record.next")
  trap 'rm -f "$record.next"' EXIT
  for status in /proc/[0-9]*/status; do
    if ! awk '$1=="NSpid:" && NF>2 && $NF==1 {found=1} END {exit !found}' "$status" 2>/dev/null; then continue; fi
    directory=${status%/status}; pid=${directory##*/}
    name=$(awk '$5=="/data" {print $4}' "$directory/mountinfo")
    case "$name" in /gateway|/v1|/v2|/v3|/v4|/v5) name=${name#/};; *) continue;; esac
    tr '\000' '\n' < "$directory/cmdline" | grep -qx '/app/scripts/fly_boot.py' || continue
    started=$(awk '{print $22}' "$directory/stat")
    namespace=$(readlink "$directory/ns/pid")
    printf '%s %s %s %s\n' "$name" "$pid" "$started" "$namespace" >> "$record.next"
  done
  test "$(wc -l < "$record.next")" -eq 6
  test "$(awk '{print $1}' "$record.next" | sort -u | wc -l)" -eq 6
  test "$(awk '{print $4}' "$record.next" | sort -u | wc -l)" -eq 6
  mv "$record.next" "$record"
  trap - EXIT
fi
test -f "$record"
while read -r name pid started namespace; do validate "$name" "$pid" "$started" "$namespace"; done < "$record"
if [ "$operation" = STOP ]; then
  trap 'while read -r name pid started namespace; do kill -CONT "$pid" || true; done < "$record"' EXIT
fi
while read -r name pid started namespace; do kill -"$operation" "$pid"; done < "$record"
sleep 0.1
while read -r name pid started namespace; do
  validate "$name" "$pid" "$started" "$namespace"
  state=$(awk '$1=="State:" {print $2}' /proc/$pid/status)
  if [ "$operation" = STOP ]; then test "$state" = T; else test "$state" != T; fi
done < "$record"
trap - EXIT
if [ "$operation" = CONT ]; then rm "$record"; fi
printf 'Verified %s for six owned namespace supervisors.\n' "$operation"
