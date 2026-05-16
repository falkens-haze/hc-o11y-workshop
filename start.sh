#!/usr/bin/env bash
set -euo pipefail

readonly OTLP_PORT=4317
readonly CONNECT_TIMEOUT=5

CYAN=$'\033[96m'
TEAL=$'\033[38;5;37m'
MAGENTA=$'\033[95m'
BOLD=$'\033[1m'
YELLOW=$'\033[1;33m'
RESET=$'\033[0m'

echo ""
echo "${CYAN}╔════════════════════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║${RESET}${BOLD}                           Cribl / Honeycomb Workshop                           ${RESET}${CYAN}║${RESET}"
echo "${CYAN}║${RESET}${BOLD}                                Telemetry Stack                                 ${RESET}${CYAN}║${RESET}"
echo "${CYAN}║${RESET}${BOLD}                                  May 20, 2026                                  ${RESET}${CYAN}║${RESET}"
echo "${CYAN}╚════════════════════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "${TEAL}  Questions or issues? Contact gcoleman@cribl.io or Slack community @greg${RESET}"
echo ""
mbox() {
  local content="$1"
  local dlen pad
  dlen=$(printf '%s' "$content" | wc -m | tr -d ' ')
  pad=$(( 80 - dlen ))
  printf "${MAGENTA}║${RESET}%s%${pad}s${MAGENTA}║${RESET}\n" "$content" ""
}
echo "${MAGENTA}╔════════════════════════════════════════════════════════════════════════════════╗${RESET}"
mbox ""
mbox "  Services that will start:"
mbox ""
mbox "  otel-collector         — receives all signals, forwards to Cribl"
mbox "  node-exporter          — host OS metrics (CPU, memory, disk, network)"
mbox "  telemetrygen-traces-*  — synthetic traces (frontend, checkout, payment)"
mbox "  workshop-logs          — logs with PII, LLM ops, HTTP events"
mbox "  genaitelgen            — synthetic GenAI/LLM spans"
mbox ""
echo "${MAGENTA}╚════════════════════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "Find your Cribl.Cloud ingest hostname in the portal:"
echo "  Workspace → Access → Public Ingress"
echo "  ${YELLOW}Docs: https://docs.cribl.io/stream/usecase-syslog-cloud#determine-your-criblcloud-ingest-address${RESET}"
echo ""
echo "Example: default.main.<organizationId>.cribl.cloud"
echo ""
read -r -p "Enter your Cribl ingest hostname: " CRIBL_HOST
echo ""

CRIBL_HOST="${CRIBL_HOST#http://}"
CRIBL_HOST="${CRIBL_HOST#https://}"
CRIBL_HOST="${CRIBL_HOST%/}"
CRIBL_HOST="${CRIBL_HOST%:*}"

if [[ -z "$CRIBL_HOST" || "$CRIBL_HOST" != *.* || "$CRIBL_HOST" == *":"* ]]; then
  echo "Invalid hostname: '${CRIBL_HOST}'"
  echo "Expected something like: default.main.<organizationId>.cribl.cloud"
  exit 1
fi

CRIBL_ENDPOINT="${CRIBL_HOST}:${OTLP_PORT}"

echo "Checking TCP connectivity to ${CRIBL_ENDPOINT} ..."
if nc -z -G "${CONNECT_TIMEOUT}" "${CRIBL_HOST}" "${OTLP_PORT}" >/dev/null 2>&1; then
  echo "Port ${OTLP_PORT} is reachable on ${CRIBL_HOST}"
else
  cat <<EOF
Cannot connect to ${CRIBL_ENDPOINT} within ${CONNECT_TIMEOUT}s.

Common causes:
  - Typo in hostname — verify in Cribl.Cloud (Workspace > Access)
  - The OpenTelemetry Source on TCP/${OTLP_PORT} isn't enabled in Cribl
  - Firewall/VPN is blocking outbound TCP/${OTLP_PORT}
  - You're not on the network required for egress to Cribl.Cloud

Resolve, then re-run ./start.sh
EOF
  exit 1
fi

cat <<EOF

Before starting the stack, set up Live Capture in Cribl so you can watch
metrics, logs, and traces arrive in real time:

  1. Open Cribl Stream
  2. Navigate to: Data > Sources > OpenTelemetry > (your source)
  3. Open the Live Data tab
  4. Click Start Capture

EOF

while true; do
  read -r -p "Type OK when Live Capture is running: " CONFIRM
  if [[ "$CONFIRM" =~ ^[Oo][Kk]$ ]]; then
    break
  fi
  echo "Type OK to proceed, or press Ctrl+C to abort."
done

echo ""
echo "Starting telemetry stack against ${CRIBL_ENDPOINT}"
echo ""
sleep 3
export CRIBL_ENDPOINT
docker compose up --remove-orphans
