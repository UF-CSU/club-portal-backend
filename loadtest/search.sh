#!/usr/bin/env bash
# Find the most people the server holds within the SLOs (p95 < 500 ms, p99 < 1 s, < 1% errors).
#
# Doubles VUS with 2-minute probes until one fails, bisects to within 10%, then confirms with a
# 5-minute hold, stepping down 10% until a hold passes.
#
#   BASE_URL=http://host:9000 TOKENS=tokens.json ./search.sh [start_vus] [max_vus]
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p results

START=${1:-100}
MAX=${2:-20000}

# probe VUS DURATION -> exit 0 if it passed the thresholds
probe() {
  local vus=$1 duration=$2 out="results/vus-$1-$2.json"
  k6 run --quiet -e VUS="$vus" -e DURATION="$duration" -e RAMP_UP=30s \
    --summary-export="$out" people.js >/dev/null 2>&1
  local code=$?
  python3 - "$out" "$vus" "$duration" "$code" <<'PY'
import json, sys
path, vus, duration, code = sys.argv[1:]
m = json.load(open(path))["metrics"]
d = m["http_req_duration"]
print(f"{'PASS' if code == '0' else 'FAIL'}  {vus:>6} people {duration:>3}  "
      f"{m['http_reqs']['rate']:7.1f} req/s  p95={d['p(95)']:6.0f}ms  p99={d['p(99)']:6.0f}ms  "
      f"errors={m['http_req_failed']['value'] * 100:.2f}%")
PY
  return $code
}

# Warm-up, not scored
k6 run --quiet -e VUS="$START" -e DURATION=1m -e RAMP_UP=15s people.js >/dev/null 2>&1

lo=0
hi=$START
while [ "$hi" -le "$MAX" ] && probe "$hi" 2m; do
  lo=$hi
  hi=$((hi * 2))
done

while [ $((hi - lo)) -gt $((hi / 10)) ]; do
  mid=$(((lo + hi) / 2))
  if probe "$mid" 2m; then lo=$mid; else hi=$mid; fi
done

vus=$lo
while [ "$vus" -gt 0 ]; do
  if probe "$vus" 5m; then
    echo "SCORE: $vus people held for 5 minutes"
    exit 0
  fi
  vus=$((vus * 9 / 10))
done
echo "SCORE: no passing hold"
exit 1
