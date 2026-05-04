#!/usr/bin/env bash
set -euo pipefail

readonly OTLP_PORT=4317
readonly CONNECT_TIMEOUT=5

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            Cribl / Honeycomb Workshop            ║"
echo "║                 Telemetry Stack                  ║"
echo "║                   May 20, 2026                   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Find your Cribl.Cloud ingest hostname in the portal:"
echo "  Workspace → Access → Public Ingress"
echo "  Docs: https://docs.cribl.io/stream/usecase-syslog-cloud#determine-your-criblcloud-ingest-address"
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
