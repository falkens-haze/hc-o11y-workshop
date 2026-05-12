# Workshop Outline — Decoupling Observability with OTel, Cribl & Honeycomb

**Audience**: architects + engineering leaders | **Duration**: 3 hours (incl. 10-min break) | **Date**: May 20, 2026

**Stack architecture**: OTel Collector → Cribl Stream → {Honeycomb (traces), Grafana Cloud (metrics), Datadog (logs), Cribl Lake (full fidelity, all signals)}

**Sources**: `telemetrygen` (3 trace services + 2 log streams) + `node-exporter` (Prometheus metrics) + `genaitelgen` (custom OTel GenAI/LLM spans)

**Outcome**: every attendee leaves with (a) a Cribl Stream Pack they authored, and (b) hands-on experience with a pre-built Cribl Search Pack against a Lakehouse-accelerated Lake dataset.

---

## Schedule


| Time        | Section                                       |
| ----------- | --------------------------------------------- |
| 0:00 – 0:10 | Welcome + prereq check                        |
| 0:10 – 0:20 | Section 1 — The 3-layer telemetry stack       |
| 0:20 – 0:40 | Section 2 — Cardinality                       |
| 0:40 – 1:05 | Section 3 — Sampling                          |
| 1:05 – 1:20 | Section 4 — Lookups                           |
| 1:20 – 1:30 | Break                                         |
| 1:30 – 1:55 | Section 5 — LLM telemetry & cost-as-a-metric  |
| 1:55 – 2:10 | Section 6 — Tracing pipelines & PII redaction |
| 2:10 – 2:40 | Section 7 — Cribl Search & Lakehouse          |
| 2:40 – 3:00 | Section 8 — Capstone: build a Cribl Pack      |


---

## Section 1 — The 3-layer telemetry stack (10 min)

- Source / Router / Destination mental model
- Tour the running stack via `docker compose ps`
- Live Capture filters: one per signal (`workshop-frontend`, `workshop-ai-assistant`, `node-exporter`, `severity_text == 'ERROR'`)

**Demos**: none — pure orientation.

---

## Section 2 — Cardinality (20 min)

- Active series = `metric × cross-product(label values)` → drives metrics bill
- High-cardinality offenders: user IDs, request IDs, container IDs, full URLs, prompt content
- Cribl mechanism: `Drop Dimensions` function on a metrics pipeline

**Demo**: drop the `cpu` label from `node_cpu_seconds_total`; show 16x series-count drop.
**Hands-on**: attendee drops a label of their choice, observes count in Grafana.

---

## Section 3 — Sampling (25 min)

Frame as **two problems, four tools** — stream-shaping vs. tail sampling. Cribl + OTel are additive, not competitive.

| Flavor                       | Where           | Trace-coherent | Outcome-aware | Best for                                                                 |
| ---------------------------- | --------------- | -------------- | ------------- | ------------------------------------------------------------------------ |
| Static `Sampling`            | Cribl Stream    | No             | No            | Logs / event streams (each event independent)                            |
| `Dynamic Sampling`           | Cribl Stream    | No             | No            | Noisy-neighbor flattening on grouped log/event streams                   |
| **OTel `tail_sampling`**     | Collector       | **Yes**        | **Yes**       | The standard for in-memory, low-latency outcome-aware trace sampling     |
| **Cribl Lake + Search**      | Search (sched.) | **Yes**        | **Yes**       | The in-storage alternative when in-memory state at scale gets expensive  |

**Framing line for the room**: *"OTel `tail_sampling` is the in-memory standard. Cribl integrates with it and adds a second architecture for when in-memory state gets expensive — same job, state in S3 instead of RAM."*

**Demos**:

1. Static Sampling — 10:1 on INFO logs, errors pass through (Cribl owns stream sampling)
2. Walkthrough of the commented `tail_sampling` block in `otel-config.yaml` — talk through each policy (errors / latency / VIP / probabilistic) and explain why we don't enable it live (telemetrygen has no variance; point at the EKS Honeycomb dataset)

(The in-storage tail-sampling counterpart — Lake + Search scheduled query — is demoed in Section 7.)

**Q&A buffer (5 min)**: handle the "but what about…?" architect questions. Common ones: can you run OTel `tail_sampling` and Cribl stream sampling together (yes, they compose); SDK-side head sampling (still valid for very high-volume services); how to choose per-service.

---

## Section 4 — Lookups (15 min)

- Enrichment via CSV/JSON files matched on an event key (out-of-band context joined onto events in flight)
- Two lookups ship with the workshop in `lookups/`:
  - `service-owners.csv` — service.name → team / business_unit / oncall_pager / criticality
  - `cloud-costs.csv` — (vendor, signal) → per-million-event cost in USD; rows for AWS, Azure, GCP, Datadog, Dynatrace, Honeycomb

**Demo 1 — Org enrichment**: upload `service-owners.csv`, attach `Lookup` function, see new fields in Live Capture; query "errors by team" in Honeycomb.
**Demo 2 — Cost estimation**: build a pipeline that joins `cloud-costs.csv`, computes per-event cost, aggregates per vendor, charts live `$/min by vendor` in Grafana. Toggle which vendor row matches on stage to re-rank in real time.
**Hands-on**: attendee adds a row to `service-owners.csv` and confirms enrichment.

---

##  Break (10 min)

---

## Section 5 — LLM telemetry & cost-as-a-metric (25 min)

- The 2026 cost problem: 4KB bodies per span × high cardinality × PII risk
- Walk through one `workshop-ai-assistant` span in Honeycomb (cost, tokens, prompt text)
- OTel GenAI semconv = same shape as OpenLLMetry/OpenLIT in production
- The Cribl move: `Aggregations` function = new signal from existing data

**Demo**: build `llm-cost-metrics` pipeline (sum cost / tokens / count by model + route), route to Grafana Prometheus, show real-time `$/sec by model` chart.
**Hands-on**: attendee replicates pipeline + route, verifies metric arrives.

**Money quote**: *"My application emitted zero of these metrics. It emitted spans. Cribl turned spans into metrics."*

---

## Section 6 — Tracing pipelines & PII redaction (15 min)

- `Mask` function on `gen_ai.prompt.0.content` for credit card / SSN / email patterns
- `Eval` function to drop prompt + completion bodies on the Honeycomb route
- Routing pattern: full LLM spans → Lake (Final = No), redacted/trimmed → Honeycomb

**Demo**: build `llm-traces-to-honeycomb` pipeline with Mask + body-drop; before/after in Honeycomb.
**Hands-on**: attendee enables Mask, confirms redacted span in Honeycomb.

---

## Section 7 — Cribl Search & Lakehouse (30 min)

- **Cribl Search** — schema-on-read, KQL, federated across providers (Cribl Lake, S3, Azure Blob, GCS, Snowflake, ClickHouse, Splunk, Elastic, etc.)
- **Lakehouse engines** — accelerated columnar layer on Cribl Lake datasets; sub-second queries that make scheduled searches and dashboards viable
- **KQL primer** — `where`, `project`, `extend`, `summarize`, `top`, `eventstats`, `join`, `mv-expand`
- The unique-to-the-router superpower: **cross-signal joins** (traces × logs × metrics) no single vendor can do

**Demos — Search Pack queries**:

1. **Service health overview** — error rate by service (basic aggregation)
2. **LLM cost leaderboard** — top 10 routes by cost (Search backstops the metric layer)
3. **PII detection sweep** — regex match on prompt content (audit/compliance angle)
4. **Cross-signal investigation** — join traces to logs on `trace_id` (**★ marquee moment — pause for emphasis**)

**Scheduled-search demo (in-storage tail sampling)**: top-N longest traces → `| send` → Stream → Honeycomb. This is the in-storage counterpart to OTel `tail_sampling` from Section 3 — same goal (keep only interesting traces), state lives in S3 instead of collector RAM, compute is ephemeral, decision latency is minutes instead of milliseconds.

**Alert-driven Search pivot demo (★ the closing moment)**: Honeycomb alert fires → runbook URL is a templated Cribl Search query → on-call clicks through → full-fidelity failing transactions in Search, including everything Cribl stripped for cost reasons. Honeycomb finds the pattern; Search finds the smoking gun. *(Replay capability is mentioned but not demoed live — it's the vendor-migration story for "Suggested next steps.")*

---

## Section 8 — Capstone: Build a Stream Pack (20 min)

Attendees **consumed** the Search Pack in Section 7. Now they **author** a Stream Pack — they're different artifacts.

Required Pack contents:

- **Pipelines**: `llm-cost-metrics`, `llm-traces-to-honeycomb`, one cardinality-control pipeline
- **Lookup**: `service-owners.csv`
- **Sample data**: captured LLM spans for offline pipeline testing
- **README**: one paragraph — what it does, what it requires, expected destinations

**Hands-on (15 min)**: each attendee builds + exports their Pack.
**Share-out (2 min)**: 3 volunteers demo their Pack name + one improvement they'd make.

---

## Presenter handoff notes

- **Pre-workshop setup**: stack must be running, Live Capture must be open before Section 1.
- **Lake data**: accumulate ≥1 hour of Lake data before Section 7 so queries return meaningful results.
- **Lakehouse**: enable on the workshop traces dataset for sub-second query response in Section 7.
- **Search Pack**: pre-load into the Cribl workspace before the workshop starts.
- **EKS dataset**: a real Honeycomb dataset is available as a "this pattern on real data" reference any time.
- **Fall-behind plan**: if running long, compress Sections 1–4 first. Sections 5–8 are the headline content.
- **Marquee moments**: (a) `$/sec by model` chart appearing live in Section 5; (b) cross-signal join in Section 7; (c) alert-driven Search pivot in Section 7; (d) Pack export in Section 8. Don't rush any of these four.

