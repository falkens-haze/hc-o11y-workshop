# Cribl / Honeycomb Workshop — Telemetry Stack

A lightweight Docker stack that emits OpenTelemetry traces, metrics, and logs
into a Cribl OTel source. Used in the Cribl / Honeycomb Workshop on May 20, 2026.

## What you'll see

| Signal | Producer | Volume |
| --- | --- | --- |
| Traces | `telemetrygen` × 3 services (`workshop-frontend`, `workshop-checkout`, `workshop-payment`) | ~33 spans/sec, with realistic per-service attributes |
| Metrics | `node-exporter` scraped by the OpenTelemetry Collector | ~100 metrics, native Prometheus naming |
| Logs | `telemetrygen` × 2 (INFO and ERROR) | 11 logs/sec, ~10:1 INFO:ERROR ratio |

All three signals ship via OTLP/gRPC to your Cribl ingest endpoint on
TCP/4317. Cribl handles the routing onward to Honeycomb (traces),
Grafana Cloud Prometheus (metrics), Grafana Cloud Loki (logs), and
Cribl Lake (full fidelity, all signals).

## Prerequisites

- Docker Desktop running (macOS or Linux)
- Bash 3.2+ (already on macOS by default)
- A Cribl.Cloud workspace with an OpenTelemetry Source listening on TCP/4317
- Network egress to your Cribl ingest hostname on TCP/4317

## Tested with

- Docker 28.2.2
- macOS Tahoe 26.3

Other recent Docker / macOS versions should work, but the above is the
combination this workshop was validated against.

## Quick start

```bash
./start.sh
```

You'll be prompted for your Cribl ingest hostname (find it in
**Cribl.Cloud → Workspace → Access → Public Ingress**, e.g.
`default.main.<organizationId>.cribl.cloud`).

The script will:

1. Validate the hostname format.
2. Test TCP connectivity to port 4317 before starting.
3. Pause and ask you to set up Live Capture in your Cribl OTel Source.
4. Run `docker compose up` to start the full stack.

## Watching data arrive

Before approving the script's "type OK" prompt, set up Live Capture so you can
see the first events as they land:

1. Open Cribl Stream.
2. Navigate to **Data > Sources > OpenTelemetry > (your source)**.
3. Open the **Live Data** tab and click **Start Capture**.
4. Return to the terminal and type `OK` to start sending.

Within ~5 seconds you should see traces, metrics, and logs flowing.

## Stopping the stack

Foreground mode (the default):

```bash
# Ctrl+C in the terminal running ./start.sh
```

Then to clean up containers:

```bash
docker compose down
```

To also remove the workshop's network and any orphaned containers from
prior versions:

```bash
docker compose down --remove-orphans
```

## Files

- `start.sh` — interactive launcher with connectivity pre-flight
- `docker-compose.yml` — defines all the producer containers and the OTel collector
- `otel-config.yaml` — OpenTelemetry Collector config (receivers, processors, exporters)
- `.gitignore` — excludes `.env` and editor/OS noise

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Cannot connect to <host>:4317` | Wrong hostname, OTel source disabled in Cribl, or firewall blocking TCP/4317 |
| Stack starts but no data in Cribl Live Capture | Live Capture not started, or wrong source selected |
| `path / is mounted on / but it is not a shared or slave mount` | Stale Docker Compose state — run `docker compose down -v` and retry |
| Metric/log fields contain dots (e.g. `service.name`) | Expected — OpenTelemetry uses dots; Cribl's destinations normalize for Prometheus/Loki conventions |

## License / use

Internal Cribl workshop materials. Not for redistribution outside Cribl.
