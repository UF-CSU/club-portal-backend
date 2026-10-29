#!/usr/bin/env bash
# Run load tests against the Vultr test box from an always-on machine.
#
#   ./vultr.sh up                      stop fly-saber (auto-restarts after 60 min), start the
#                                      test stack, open ports 9000/9300 to this machine only
#   ./vultr.sh run go-400 9300 400     people scenario: LABEL PORT PEOPLE [CHECKIN_ATTENDEES]
#   ./vultr.sh down                    stop the test stack, restore fly-saber, close the ports
#
# Ports: 9000 = Django only, 9300 = Go in front of Django.
# Env: VPS (default root@64.177.52.103), SSH_KEY (default ~/.ssh/id_ed25519),
#      TOKENS (default ./tokens.json), DEADMAN_MINUTES (default 60)
set -euo pipefail
cd "$(dirname "$0")"

VPS=${VPS:-root@64.177.52.103}
HOST=${VPS#*@}
SSH_KEY=${SSH_KEY:-$HOME/.ssh/id_ed25519}
TOKENS=${TOKENS:-$PWD/tokens.json}
DEADMAN_MINUTES=${DEADMAN_MINUTES:-60}
COMPOSE="docker compose -f loadtest/docker-compose.yml --env-file loadtest/.env"

remote() {
  ssh -i "$SSH_KEY" -o ConnectTimeout=15 -o ServerAliveInterval=5 -o ServerAliveCountMax=6 "$VPS" "$@"
}

up() {
  local ip
  ip=$(curl -s -m 10 https://api.ipify.org)
  echo "Opening ports 9000 and 9300 to $ip"
  remote "set -e
    setsid nohup sh -c 'sleep $((DEADMAN_MINUTES * 60)); docker start fly-saber' >/dev/null 2>&1 < /dev/null &
    echo \$! > /root/flysaber-deadman.pid
    docker stop fly-saber >/dev/null
    echo \"fly-saber stopped, auto-restart at \$(date -u -d '+$DEADMAN_MINUTES min' +%H:%M) UTC\"
    cd /root/club-portal-loadtest
    $COMPOSE start >/dev/null 2>&1
    docker start clubs-go >/dev/null
    for port in 9000 9300; do
      iptables -I DOCKER-USER -p tcp -m conntrack --ctorigdstport \$port --ctdir ORIGINAL ! -s $ip -j DROP
    done
    for i in \$(seq 1 60); do curl -sf -o /dev/null localhost:9000/api/v1/club/tags/ && break; sleep 2; done
    echo 'test stack is up'"
}

down() {
  remote "cd /root/club-portal-loadtest
    docker stop clubs-go >/dev/null 2>&1 || true
    $COMPOSE stop >/dev/null 2>&1 || true
    iptables -S DOCKER-USER | grep -E 'ctorigdstport (9000|9300) ' | sed 's/^-A /-D /' | while read -r rule; do iptables \$rule; done
    docker start fly-saber >/dev/null
    for i in \$(seq 1 30); do [ \"\$(docker inspect -f '{{.State.Health.Status}}' fly-saber)\" = healthy ] && break; sleep 2; done
    if [ -f /root/flysaber-deadman.pid ]; then kill \$(cat /root/flysaber-deadman.pid) 2>/dev/null || true; rm -f /root/flysaber-deadman.pid; fi
    echo \"fly-saber: \$(docker inspect -f '{{.State.Health.Status}}' fly-saber), test ports closed\""
}

# CPU seconds used so far by the Django app, Go and Postgres containers
server_cpu() {
  remote 'for c in clubs-loadtest-app-1 clubs-go clubs-loadtest-postgres-1; do
    printf "%s " $(docker exec $c cat /sys/fs/cgroup/cpu.stat 2>/dev/null | awk "/usage_usec/{print \$2}" || echo 0)
  done'
}

run() {
  local label=$1 port=$2 people=$3 attendees=${4:-0}
  mkdir -p results
  local before after code=0
  before=$(server_cpu)
  k6 run --quiet --summary-export="results/$label.json" -e BASE_URL="http://$HOST:$port" -e TOKENS="$TOKENS" \
    -e VUS="$people" -e RAMP_UP=20s -e DURATION=2m -e ATTENDEES="$attendees" -e POLL_ID=1242 \
    -e CHECKIN_AT=30s -e ARRIVAL_S=60 people.js >/dev/null 2>&1 || code=$?
  after=$(server_cpu)

  python3 - "results/$label.json" "$label" "$code" "$before" "$after" <<'PY'
import json, sys
path, label, code, before, after = sys.argv[1:]
m = json.load(open(path))["metrics"]
d, n = m["http_req_duration"], m["http_reqs"]["count"]
b, a = [int(x) for x in before.split()], [int(x) for x in after.split()]
cpu = [(y - x) / 1e6 for x, y in zip(b, a)]

if d["max"] > 61000:
    verdict = "INVALID (load generator stalled)"  # k6 times requests out at 60 s
elif m.get("http_req_connecting", {}).get("p(95)", 0) > 100:
    verdict = "INVALID (slow network)"
else:
    verdict = "PASS" if code == "0" else "FAIL"

line = (f"{verdict:6} {label:18} {m['http_reqs']['rate']:6.1f} req/s  p95={d['p(95)']:5.0f}ms  "
        f"p99={d['p(99)']:5.0f}ms  errors={m['http_req_failed']['value'] * 100:.2f}%  "
        f"| CPU s: django={cpu[0]:.1f} go={cpu[1]:.1f} postgres={cpu[2]:.1f}  {sum(cpu) * 1e3 / n:.1f} ms/req")
submit = m.get("http_req_duration{name:submit}")
if submit and submit.get("max", 0) > 0:
    line += f"  | submit p95={submit['p(95)']:.0f}ms"
print(line)
PY
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  run) shift; run "$@" ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
