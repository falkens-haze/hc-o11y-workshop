# Cribl / Honeycomb Workshop — Telemetry Stack

A lightweight Docker stack that emits OpenTelemetry traces, metrics, logs, and
LLM telemetry into a Cribl OTel source. Used in the Cribl / Honeycomb Workshop
on May 20, 2026.

## What you'll see

| Signal | Source | Volume |
| --- | --- | --- |
| Traces | `telemetrygen` × 3 services (`workshop-frontend`, `workshop-checkout`, `workshop-payment`) | ~33 spans/sec, with realistic per-service attributes |
| Metrics | `node-exporter` scraped by the OpenTelemetry Collector | ~100 metrics, native Prometheus naming |
| Logs | `telemetrygen` × 2 (INFO and ERROR) | 11 logs/sec, ~10:1 INFO:ERROR ratio |
| LLM telemetry | `genaitelgen` (custom — see `genaitelgen/`) | 2 traces/sec (~5 spans/sec), OTel GenAI semconv shape, with prompts/completions, token counts, per-call cost, and a 3% error rate |

All four signals ship via OTLP/gRPC to your Cribl ingest endpoint on
TCP/4317. Cribl handles the routing onward to Honeycomb (traces),
Grafana Cloud Prometheus (metrics), Grafana Cloud Loki (logs), and
Cribl Lake (full fidelity, all signals).

### About the LLM signal

`genaitelgen` is a small Python container that emits synthetic LLM traces
following the [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai),
with the same attribute shape that OpenLLMetry and OpenLIT produce in real
production deployments. Each "request" is a small parent/child trace:

```
SERVER  POST /api/v1/chat/<route>
├── CLIENT  embedding text-embedding-3-small   (~30% of requests)
├── CLIENT  chat <model>                        (always — the LLM call)
└── CLIENT  execute_tool <tool_name>            (~10% of requests)
```

LLM spans include:

- `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`
- `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cost`
- `gen_ai.prompt.0.content` and `gen_ai.completion.0.content` (full text bodies)
- A mix of OpenAI, Anthropic, and AWS Bedrock models with realistic pricing
- Occasional `length` truncations, `content_filter` refusals, and `rate_limit_exceeded` errors

A handful of prompts intentionally embed obvious test-data PII patterns
(Stripe's `4242 4242 4242 4242` test card, the reserved `555-0100` phone
range, the well-known invalid SSN `123-45-6789`) so attendees can demo Cribl
Mask functions on data that's universally recognized as fake.

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
LLM spans from `genaitelgen` arrive after the image builds (~30s on first run).

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
- `docker-compose.yml` — defines all the source containers and the OTel collector
- `otel-config.yaml` — OpenTelemetry Collector config (receivers, processors, exporters).
  Includes an active `memory_limiter` and a commented-out `tail_sampling`
  example you can enable for advanced trace-policy demos.
- `genaitelgen/` — synthetic LLM telemetry generator
  - `main.py` — the OTel GenAI span emitter
  - `Dockerfile` — slim Python 3.12 container
  - `requirements.txt` — pinned OTel SDK versions
- `lookups/` — CSV lookup tables used by the workshop demos
  - `service-owners.csv` — `service.name` → team / business_unit / oncall_pager / criticality
  - `cloud-costs.csv` — list-price approximations for AWS, Azure, GCP, Datadog, Dynatrace, Honeycomb (per-million-event normalized; see file header)
- `.gitignore` — excludes `.env` and editor/OS noise

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Cannot connect to <host>:4317` | Wrong hostname, OTel source disabled in Cribl, or firewall blocking TCP/4317 |
| Stack starts but no data in Cribl Live Capture | Live Capture not started, or wrong source selected |
| `path / is mounted on / but it is not a shared or slave mount` | Stale Docker Compose state — run `docker compose down -v` and retry |
| Metric/log fields contain dots (e.g. `service.name`) | Expected — OpenTelemetry uses dots; Cribl's destinations normalize for Prometheus/Loki conventions |
| `genaitelgen` build is slow on first start | Expected — `pip install` runs once and is cached; subsequent `docker compose up` calls are instant |
| No `gen_ai.*` spans in Cribl Live Capture | Make sure the `genaitelgen` container is running (`docker compose ps`); the build can take 30s on a cold cache |

## License / use

Internal Cribl workshop materials. Not for redistribution outside Cribl.
