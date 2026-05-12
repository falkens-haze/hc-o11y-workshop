# Workshop: Decoupling Observability with OpenTelemetry, Cribl, and Honeycomb

**Audience**: architects and engineering leaders responsible for observability strategy
**Duration**: 3 hours (includes one 10-minute break)
**Outcome**: attendees leave with a working Cribl Pack and a repeatable architectural blueprint they can take back to their org

---

## Schedule at a glance

| Time | Section | Format |
| --- | --- | --- |
| 0:00 – 0:10 | Welcome, prereq check, stack-up verification | Talk + check-in |
| 0:10 – 0:20 | The 3-layer telemetry stack | Tour + slides |
| 0:20 – 0:40 | Cardinality: the silent metrics killer | Concept + demo + hands-on |
| 0:40 – 1:05 | Sampling: stream-shaping vs. tail sampling | Concept + two demos |
| 1:05 – 1:20 | Lookups: enrichment as a first-class operation | Concept + demo + hands-on |
| 1:20 – 1:30 | **Break** | |
| 1:30 – 1:55 | LLM telemetry & cost-as-a-metric | Concept + demo + hands-on |
| 1:55 – 2:10 | Tracing pipelines & PII redaction | Concept + demo + hands-on |
| 2:10 – 2:40 | Cribl Search & Lakehouse | Concept + Search Pack tour + scheduled search + alert pivot |
| 2:40 – 3:00 | Capstone: build your own Cribl Pack | Hands-on exercise + share-out |

---

## Prerequisites

Each attendee needs:

- Docker Desktop running
- Their own Cribl.Cloud workspace (free tier is fine — `1 TB/day`) including Cribl Lake and Cribl Search
- A Honeycomb account (free tier) — destination for traces
- A Grafana Cloud account (free tier) — destination for metrics (Prometheus)
- A Datadog account (free trial) — destination for logs
- The workshop Search Pack pre-loaded into their Cribl Search workspace
- The workshop repo cloned and the stack running via `./start.sh`

A 10-minute pre-flight at the top of the workshop confirms everyone has data flowing into Cribl Live Capture before we begin.

---

# Section 1 — The 3-layer telemetry stack (10 min)

**Goal**: align everyone on the architectural pattern before we touch any pipeline.

## The pitch (2 min)

Most observability stacks are 2-layer: sources (your apps and infra) talk directly to destinations (Datadog, Splunk, etc.). This couples vendor choice to source code. To migrate vendors you touch every service.

The 3-layer pattern inserts a **router** between the two:

```
    Sources            Router            Destinations
   ────────────      ───────────       ─────────────────────────
   apps + infra  →   Cribl Stream  →   Honeycomb       (traces)
                                   →   Grafana Cloud   (metrics)
                                   →   Datadog         (logs)
                                   →   Cribl Lake      (full fidelity, all signals)
                                                       ↳ queryable via Cribl Search
```

Four destinations, one router. Each backend gets the signal it's best at, full fidelity is preserved in Lake, and every signal is queryable via Cribl Search. The router decouples vendor choice from instrumentation choice. The instrumentation standard is **OpenTelemetry**: vendor-neutral, owned by CNCF, supported by every major backend.

## Tour the running stack (5 min)

Pull up `docker compose ps` on stage and walk through what each container is doing:

| Container | Role |
| --- | --- |
| `otel-collector` | The OTel Collector — receives OTLP, batches, applies the `memory_limiter`, forwards to Cribl |
| `telemetrygen-traces-frontend/checkout/payment` | Three "services" emitting trace spans at different rates with realistic per-service attributes |
| `telemetrygen-logs-info` / `-error` | Two log streams blended ~10:1 INFO:ERROR |
| `node-exporter` | A real Prometheus metrics source — scraped by the OTel Collector |
| `genaitelgen` | Custom Python container emitting OTel GenAI-shaped LLM traces |

**Key teaching point**: notice that the sources emit *only* OTLP. They have no idea Honeycomb exists. They have no idea Grafana exists. The router knows. **Vendor knowledge lives in one place.**

## What attendees should see in Live Capture (3 min)

Walk them through the OTel Source's Live Data tab. Filter on:

- `service.name == 'workshop-frontend'` → trace data
- `service.name == 'workshop-ai-assistant'` → LLM traces
- `service.name == 'node-exporter'` → metrics
- `severity_text == 'ERROR'` → error logs

**Takeaway**: "The router is where every observability decision lives. The rest of your stack is just data flowing past it."

---

# Section 2 — Cardinality: the silent metrics killer (20 min)

**Goal**: make attendees feel the cost of unbounded label cardinality, then show how Cribl gives operators a control plane for it.

## The pitch (3 min)

Every unique combination of metric name + label values creates a new time series. Time series cost money — Grafana Cloud, Datadog, New Relic all bill on active series count. A single high-cardinality label like `user_id` or `request_id` can multiply your bill by 1000x with one bad commit.

The sources don't know this. They emit what they emit. The fix has historically required:
- A code change to drop the label, OR
- A re-instrumentation effort across many services

Cribl makes it a **30-second routing decision**.

## Concept (5 min)

- Cardinality = `metric_name × cross-product(label_values)`
- Backend cost is roughly proportional to active series count
- High-cardinality labels: user IDs, request IDs, full URLs, container IDs, IP addresses, prompt content
- Low-cardinality labels: service name, region, environment, HTTP status code (3-digit), model name

**Cribl mechanism**: the `Drop Dimensions` function (or `Eval` → `_metric_dim` removal) on a metrics pipeline.

## Demo (7 min)

Use node-exporter data, which has plenty of dimensions. Pick a metric like `node_cpu_seconds_total` which has labels: `cpu`, `mode`, `instance`.

In a metrics pipeline:

| Function | Configuration |
| --- | --- |
| `Drop Dimensions` | Remove `cpu` from any metric matching `node_cpu_seconds_total` |

Show before/after in Capture: 16 cores × 8 modes = 128 series collapses to 8. Same insight, 16x cheaper.

## Hands-on (5 min)

Each attendee:
1. Open the metrics pipeline
2. Add a `Drop Dimensions` function dropping the `cpu` label
3. Observe the active series count drop in their Grafana Prometheus

**Takeaway**: "Your metrics bill is a label-management problem. Cribl makes label management a routing decision, not a code change."

---

# Section 3 — Sampling: stream-shaping vs. tail sampling (25 min)

**Goal**: distinguish where each tool in the stack does its sampling job, and frame Cribl + OTel as additive, not competitive.

## The pitch (3 min)

The naive answer to "my telemetry is expensive" is sampling. But "sampling" actually breaks into two different problems with different right tools:

1. **Stream sampling** — thin out high-volume, low-value events as they flow past. Best done at the router. Cribl owns this.
2. **Tail sampling** — keep traces only after seeing how they finished (errors, latency, attributes). This needs trace state. The OTel community standardized this years ago; Cribl integrates with their work and adds a second architecture for when in-memory state gets expensive.

We'll cover four flavors total — two on the stream-shaping side, two on the tail-sampling side. Pick the right tool, not the most-buzz-worthy.

## The four flavors (8 min)

| Flavor | Where it runs | Trace-coherent? | Outcome-aware? | Best for |
| --- | --- | --- | --- | --- |
| **Static** (Cribl `Sampling`) | Cribl Stream pipeline | No | No | Logs and event streams where each event stands alone |
| **Volume-adaptive** (Cribl `Dynamic Sampling`) | Cribl Stream pipeline | No | No | Noisy-neighbor flattening on logs grouped by host/route/etc. |
| **In-memory tail** (OTel `tail_sampling`) | OTel Collector | **Yes** | **Yes** | The standard. Real-time outcome-aware sampling, paid for in collector RAM. |
| **In-storage tail** (Cribl Lake + Search) | Cribl Search, scheduled | **Yes** | **Yes** | The same outcome-aware result with state in cheap S3 instead of expensive RAM — at the cost of latency to APM. |

The framing for the room:

> *"OTel `tail_sampling` is the in-memory standard for trace-aware sampling. We're not going to try to replace it — Cribl integrates with it. Where Cribl adds value is on the OTHER side of the cost equation: when in-memory state at scale gets expensive, Cribl Lake + Search lets you do the same job with state in S3 instead. Two valid architectures. You pick where the state lives."*

This is the line that lifts OTel (and by extension Honeycomb's OTel investment) while positioning Cribl as the integrator and the storage-side alternative.

## Demo 1 — Static Sampling on logs (4 min)

Add a `Sampling` function to the logs pipeline:
- Filter: `severity_text == 'INFO'`
- Sample Rate: `10`

INFO logs drop 10:1; ERROR logs pass through untouched. Show in Datadog.

This is the classic stream-shaping pattern. Notice it's a *log* demo — Cribl's stream sampling is the right tool for events, not for traces (each span is an independent event from the function's perspective; you'd shred your traces).

## Demo 2 — OTel `tail_sampling` walkthrough (5 min)

Open `otel-config.yaml` on screen and walk through the commented `tail_sampling` block. Talk through each policy:

- `status_code: ERROR` — keep every failed trace
- `latency: > 500ms` — keep every slow trace
- `string_attribute: customer.tier=premium` — keep every VIP trace
- `probabilistic: 5%` — sample the rest

**Why we're not enabling it live**: telemetrygen produces uniform, error-free, fast traces — there's no variance for the policies to find. This is the moment to point at the EKS Honeycomb dataset where the same processor *is* enabled and you can show real outcomes being preserved.

**Talking point**: "This processor lives in the OTel Collector — closest to source, lowest decision latency, owned by the OTel community. Cribl doesn't have an in-memory equivalent and that's by design. We use the right tool for the right job."

Forward-pointer to Section 7: "When the in-memory tax for `tail_sampling` gets expensive at scale, Cribl gives you a second architecture for the same job — state in Lake, queries in Search. We'll see that pattern shortly."

**Takeaway**: "Stream sampling is a Cribl problem. Tail sampling is a state-management problem — solve it in OTel's memory or Cribl's storage, depending on your constraints. Honeycomb consumes the curated output of either."

## Q&A buffer (5 min)

Sampling is the section that produces the most architect questions ("but what about my…?"). Use this buffer to take 2–3 questions before moving on. Common ones to be ready for:

- "Can I run OTel `tail_sampling` *and* Cribl stream sampling at the same time?" — Yes. Tail sampling decides which traces survive; Cribl shapes whatever survives. They compose.
- "What about head-based probabilistic sampling in the SDK?" — Still valid for very high-volume services where you can't afford to even ship every span to the collector. Layered with tail sampling downstream, you get coarse + fine control.
- "How do I move from one to the other?" — You don't have to. Pick per-service or per-environment based on cost vs. latency tradeoffs.

---

# Section 4 — Lookups: enrichment as a first-class operation (15 min)

**Goal**: show that Cribl can turn flat telemetry into team-aware, owner-aware, **cost-aware** data without changes to sources.

## The pitch (2 min)

Every observability question eventually becomes "who owns this?", "which business unit is responsible?", or "what would this cost in vendor X?" The answer is rarely in the telemetry itself — it lives in spreadsheets, CMDBs, and tribal knowledge.

Cribl `Lookup` joins that out-of-band context onto every event in flight. No source changes, no schema migration.

## Concept (2 min)

- Lookup file = CSV (or JSON) with a key column and one or more enrichment columns
- The function matches an event field against the key column and adds the row's other columns to the event
- Lookups can be deployed centrally and updated independently of pipelines

The workshop ships with two lookups in `lookups/`:

| File | Keyed on | What it adds |
| --- | --- | --- |
| `service-owners.csv` | `service.name` | `team`, `business_unit`, `oncall_pager`, `criticality` |
| `cloud-costs.csv` | `(vendor, signal)` | `cost_per_unit_usd`, `pricing_basis`, `assumed_event_size_kb` |

## Demo 1 — Org-chart enrichment (4 min)

1. Upload `lookups/service-owners.csv` as a Lookup file in Cribl.
2. Add a `Lookup` function to a trace pipeline:
   - Lookup file: `service-owners.csv`
   - Lookup field in event: `service.name`
   - Lookup field in lookup: `service.name`
   - Output: append all columns
3. Show in Capture: spans now carry `team`, `business_unit`, `oncall_pager`, `criticality`.

In Honeycomb, query "errors grouped by team" or "spans where criticality = tier-0".

## Demo 2 — Cost-estimation enrichment (5 min)

This is the demo that closes the cost-narrative loop. We're going to estimate, in real time, **what it would cost to ship our running telemetry to each of the major cloud vendors and APM tools.** Then we'll turn that into a metric and chart it in Grafana.

The lookup `cloud-costs.csv` has rows for AWS, Azure, GCP, Datadog, Dynatrace, and Honeycomb — one row per `(vendor, signal)`. List-price approximations from each vendor's public pricing page, normalized to per-million-events for traces/logs and per-million-datapoints for metrics.

The pipeline pattern:

```
[event arrives]
     │
     ▼
Eval     →  set __signal = "traces" | "logs" | "metrics"  based on event shape
     │
     ▼
For each vendor (or one selected vendor at a time):
   Lookup    →   match (vendor=aws, signal=__signal) → adds cost_per_unit_usd
     │
     ▼
Eval        →   __est_cost_usd = cost_per_unit_usd / 1_000_000
     │
     ▼
Aggregations → sum(__est_cost_usd) by __signal, vendor in 30s windows
     │
     ▼
Grafana destination (re-use existing route)
```

Result in Grafana: a **live $/min chart by vendor** showing what each backend would cost for the workshop's current event mix. Switch destinations on stage by toggling which vendor row the Lookup matches — watch the chart re-rank in front of attendees.

**Talking point**: *"We just turned a CSV file from your finance team into a real-time cost forecast. The lookup table is the contract between ops and finance — when prices change, finance updates the CSV, and every observability decision in the org reprices automatically."*

## Hands-on (2 min)

Each attendee:
1. Add a row to `service-owners.csv` for a service in their org
2. Confirm the new row's enrichment lands in Live Capture

(The cost-estimation pipeline is too involved for a 2-minute hands-on — they'll bundle it into their Pack in Section 8 instead.)

**Takeaway**: "Cribl lets ops own the metadata — and finance own the cost model — without bothering devs. The router is the integration surface between three teams that traditionally don't share schemas."

---

## ☕ Break (10 min)

---

# Section 5 — LLM telemetry & cost-as-a-metric (25 min)

**Goal**: introduce AI observability as the marquee 2026 use case for the routing pattern.

## The pitch (5 min)

LLM telemetry is the canonical Cribl Stream pitch in 2026. Three reasons it's expensive on every axis:
1. **Volume per span** — prompt and completion bodies are kilobytes
2. **Cardinality** — every prompt is unique
3. **PII / IP exposure** — prompts contain customer data, source code, internal docs

Pull up one of the `workshop-ai-assistant` spans in Honeycomb and read it line by line. The shock moments:
- "This single span is ~4KB."
- "Cost was $0.000554 for one call. Multiply by your real call volume."
- "Look — `alice@example.com`. In a real system this could be a credit card or an SSN. In our generator, sometimes it actually is — let's prove it."

Filter on `gen_ai.prompt.0.content =~ '4242'`. Watch the Stripe test card show up.

## Concept (5 min)

The source side: OTel GenAI semantic conventions are the standard. OpenLLMetry and OpenLIT are the dominant production instrumentations and use this exact attribute shape.

The router side: the Aggregations function turns raw spans into derived metrics. This is **new signal from existing data**.

## Demo — Cost metrics to Grafana (10 min)

Build the pipeline live:

**Pipeline `llm-cost-metrics`** with one function:

| Setting | Value |
| --- | --- |
| Function | `Aggregations` |
| Time Window | `30s` |
| Aggregations | `sum('gen_ai.usage.cost').as('llm_cost_usd')`<br>`sum('gen_ai.usage.total_tokens').as('llm_tokens_total')`<br>`count().as('llm_call_count')` |
| Group By | `gen_ai.request.model`, `app.route`, `service.name`, `gen_ai.system` |
| Output Mode | Metrics |

Add a Route:
- Filter: `service.name == 'workshop-ai-assistant' && gen_ai && gen_ai.usage && gen_ai.usage.cost != null`
- Pipeline: `llm-cost-metrics`
- Destination: existing Grafana Cloud Prometheus
- Final: No

Then in Grafana:
```promql
sum by (gen_ai_request_model) (rate(llm_cost_usd[1m]))
```

Watch a real-time `$/sec by model` chart appear. **Make the meta-observation explicit**:

> "My application emitted exactly zero of these metrics. It emitted spans. Cribl turned spans into metrics. That is the routing-layer pattern in one sentence."

## Hands-on (5 min)

Attendees replicate the pipeline + route in their own Cribl workspace and verify the metric arrives in their Grafana.

**Takeaway**: "AI is making telemetry expensive. The routing layer is the only place you can shape it without touching application code."

---

# Section 6 — Tracing pipelines & PII redaction (15 min)

**Goal**: show body redaction and Lake-First in action on the LLM traces.

## The pitch (2 min)

We just showed Cribl can derive metrics from traces. Now we'll show it can also **make those traces safe and cheap to send to an APM vendor** at the same time, while preserving full fidelity to Lake.

## Demo — Mask PII + drop bodies to Honeycomb (8 min)

**Pipeline `llm-traces-to-honeycomb`** with two functions:

**Function 1: Mask** (PII redaction)

| Field | Pattern | Replacement |
| --- | --- | --- |
| `gen_ai.prompt.0.content` | `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b` | `***CARD***` |
| `gen_ai.prompt.0.content` | `\b\d{3}-\d{2}-\d{4}\b` | `***SSN***` |
| `gen_ai.prompt.0.content` | `\b[\w.+-]+@[\w-]+\.[\w.-]+\b` | `***EMAIL***` |

**Function 2: Eval** (body trim for cost)

| Action | Field |
| --- | --- |
| Remove field | `gen_ai.prompt.0.content` (after redaction; the metadata is still useful) |
| Remove field | `gen_ai.completion.0.content` |

Show before/after in Capture and Honeycomb.

**Routing pattern**:
- Route 1: full LLM spans → Cribl Lake (Final = No)
- Route 2: same LLM spans → `llm-traces-to-honeycomb` pipeline → Honeycomb destination

Honeycomb gets the metadata — model, tokens, cost, latency, finish_reason, route, user.
Lake gets the bodies for replay, eval, audit.

## Hands-on (5 min)

Each attendee adds the Mask function and confirms a redacted span in Honeycomb.

**Takeaway**: "You don't have to choose between observability and privacy. The router does both."

---

# Section 7 — Cribl Search & Lakehouse (30 min)

**Goal**: introduce Cribl Search and the Lakehouse engines as the analytical layer that makes Lake-First viable, and close with the alert-driven Search pivot — the operational bridge between Honeycomb and Cribl Search.

## The pitch (4 min)

We've already routed all four signals — traces, metrics, logs, LLM telemetry — to Cribl Lake at full fidelity. That's a great storage decision and a terrible one if querying that data is slow or expensive.

Lake-First only works if **you can answer questions against the Lake at speed.** Cribl Search and the new Lakehouse engines are what make that possible. Without them, Lake-First is just an archive. With them, Lake-First is a strategic asset:

- Honeycomb answers your **trace** questions
- Grafana answers your **metric** questions
- Datadog answers your **log** questions
- **Cribl Search answers all of them — and any cross-signal question that no individual vendor can.**

That last bullet is the unique capability. No vendor can join your Honeycomb traces to your Datadog logs to your Grafana metrics. Cribl Search can, because Cribl Lake holds all of them in one substrate, queryable through one engine, in one query language ([Kusto Query Language / KQL](https://docs.cribl.io/search/search-your-data/)).

## Concept: Cribl Search (4 min)

The fundamentals:

- **Schema-on-read**: no ingest cost, no indexing cost. Query data where it lives — Cribl Lake, Amazon S3, Azure Blob, GCS, Snowflake, ClickHouse, Elasticsearch, Splunk, and more — through a unified KQL surface.
- **KQL** as the query language: the same dialect Azure Data Explorer made popular. Familiar to anyone who's used Azure Monitor; learnable in an afternoon if not.
- **Federated search**: a single query can span multiple Dataset Providers. "Show me errors across my Cribl Lake **and** my legacy Splunk **and** my AWS Security Lake" — one query, joined results.
- **No vendor lock-in on data**: your data stays in your object store. Cribl Search reads it. You can leave Cribl tomorrow and your data is still in S3 or Lake in open Parquet format.

## Concept: Lakehouse engines (4 min)

Standard Cribl Search reads raw data from object storage. That's cheap to store and slow to query — fine for ad-hoc investigation, painful for dashboards or scheduled searches.

**Lakehouse engines** are Cribl's accelerated query layer for Cribl Lake datasets. They take the raw newline-delimited JSON or compressed flat files in your Lake datasets and maintain an optimized columnar representation alongside, so that:

- Queries that previously took 30+ seconds return in **sub-second** time
- Scheduled searches run cheaply and frequently
- Dashboards can drive against Lake directly instead of needing data duplication
- The same KQL query syntax works against accelerated and non-accelerated datasets — only the speed changes

The mental model: Lakehouse is to Cribl Lake what BigQuery is to Google Cloud Storage, what Snowflake is to S3, what Athena+Iceberg is to Amazon S3. It's the **query acceleration tier** that turns a cheap object store into a real-time analytical surface.

You only enable Lakehouse on the datasets where it pays off (high-volume, frequently queried). Lower-volume or compliance-only datasets can stay on the default engine to save cost.

## KQL primer (3 min)

Just enough syntax to follow what comes next. KQL pipelines flow left-to-right, like Unix shell:

```kql
dataset="workshop-otel-traces"        // pick a dataset
| where service.name == "workshop-payment"   // filter
| where status_code == 2                     // status_code 2 = ERROR in OTLP
| summarize count() by app.route             // aggregate
| top 5 by count_                             // sort + limit
```

The handful of operators you'll see in the Search Pack:

| Operator | What it does |
| --- | --- |
| `where` | filter rows by predicate |
| `project` / `project-away` | select / drop columns |
| `extend` | add a computed column |
| `summarize` | group + aggregate |
| `top` / `take` / `limit` | row limiting |
| `eventstats` | windowed stats merged back onto each row |
| `join` | combine datasets on a key |
| `mv-expand` | flatten an array column into rows |
| `cribl find` | full-text search across one or many datasets |

## Search Pack tour (8 min)

Open the workshop's Search Pack and walk through 4 representative queries — the goal is to model the *kinds* of questions Search uniquely answers, so attendees know what to write themselves.

**Query 1 — Service health overview**

```kql
dataset="workshop-otel-traces"
| where _time > ago(1h)
| summarize total = count(), errors = countif(status_code == 2) by service.name
| extend error_rate_pct = round(100.0 * errors / total, 2)
| order by error_rate_pct desc
```

Demonstrates basic aggregation. Compare to "build the same dashboard in Honeycomb, in Grafana, and in Datadog" — you'd build it three times. In Search you build it once against Lake.

**Query 2 — LLM cost leaderboard**

```kql
dataset="workshop-otel-traces"
| where service.name == "workshop-ai-assistant"
| where isnotnull(gen_ai.usage.cost)
| summarize total_cost_usd = round(sum(gen_ai.usage.cost), 4),
            calls = count()
        by gen_ai.request.model, app.route
| order by total_cost_usd desc
| take 10
```

Demonstrates that the cost metric we put in Grafana in Section 5 is also queryable as raw data in Search — and at higher resolution, with no pre-aggregation needed. "If you forgot to create the metric ahead of time, Search has your back."

**Query 3 — PII detection sweep**

```kql
dataset="workshop-otel-traces"
| where isnotnull(gen_ai.prompt.0.content)
| where gen_ai.prompt.0.content matches regex @"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
   or gen_ai.prompt.0.content matches regex @"\b\d{3}-\d{2}-\d{4}\b"
| project _time, service.name, app.route, app.user, gen_ai.prompt.0.content
| order by _time desc
```

Demonstrates the audit/compliance use case. "Cribl Stream's Mask function redacts in flight. Cribl Search proves we caught everything — and finds the ones we missed."

**Query 4 — Cross-signal investigation**

```kql
dataset="workshop-otel-traces"
| where status_code == 2
| project trace_id, error_service = service.name, error_time = _time
| join kind=inner (
      dataset="workshop-otel-logs"
      | where severity_text == "ERROR"
      | project trace_id, log_message = body, log_service = service.name
  ) on trace_id
| project error_time, trace_id, error_service, log_service, log_message
```

Demonstrates the cross-signal join. **No individual vendor can do this.** Honeycomb has the trace, Datadog has the log, but they don't talk to each other. Search joins them in one query because Lake holds both.

This is the **unique-to-the-router-pattern** moment — make a beat of it.

## Demo: scheduled search → in-storage tail sampling (4 min)

This is the **second tail-sampling architecture** we previewed back in Section 3 — the in-storage counterpart to OTel `tail_sampling`'s in-memory approach.

1. Take Query 2 (or a "longest traces" variant) and **save it as a Scheduled Search** that runs every hour.
2. Append `| send` to the query, pointing at a Cribl Stream destination → Honeycomb.
3. Result: Honeycomb gets the 10 most expensive LLM calls per hour, automatically. Lake retains everything.

Walk through the [Patrick Wade pattern](https://cribl.io/blog/mastering-tail-sampling-for-opentelemetry-cost-effective-strategies-with-cribl/) at the architectural level: state in S3, compute ephemeral, no memory tax in the live path, arbitrarily complex policies because they're just KQL queries.

The key contrast to land: **same goal as OTel `tail_sampling` — keep only the interesting traces — different storage model.** OTel keeps state in collector RAM; Cribl Lake + Search keeps it in object storage. OTel decides in milliseconds; Cribl decides in minutes. Both are valid. Pick the architecture that matches your scale, your budget, and your latency tolerance.

## Demo: alert-driven Search pivot (3 min, the close)

The operational pairing to the scheduled-search demo. Scheduled-search pushes data *from* Search *to* Honeycomb. The alert pivot goes the other way — a Honeycomb alert that drills *into* Cribl Search for full fidelity.

The flow (mock it on stage with a saved alert or screenshot):

1. **Honeycomb fires an alert** — e.g., "error rate on `workshop-payment` > 5% in the last 5 minutes."
2. The alert's **runbook URL** is a Cribl Search query template with the alert's context variables filled in:
   ```
   dataset="workshop-otel-traces"
   | where _time > ago(15m)
   | where service.name == "${service}"
   | where status_code == 2
   | project _time, trace_id, app.route, status_message, error.type
   | order by _time desc
   ```
3. The on-call clicks the link. Cribl Search opens the query against Lake. They see the **full-fidelity failing transactions** — including all the fields Cribl stripped from Honeycomb for cost reasons (full prompt bodies, complete trace context, stack traces if your real traces have them).

This is the answer to the question every Honeycomb customer asks: *"What if I need the data Cribl shaped away?"* The answer: it's one click away, always.

The architecture: Honeycomb provides the **pattern recognition** (analytical, sampled, fast). Cribl Search provides the **forensic detail** (full fidelity, on-demand, in Lake). They aren't competitors — they're co-conspirators.

(Inspired by Scott Beamish's [APM cost optimization blog](https://cribl.io/blog/optimizing-apm-costs-and-visibility-with-cribl-stream-and-search/) — see presenter notes for the original walkthrough.)

**Note on Replay**: we're not demoing Cribl Stream's Replay-from-Lake feature in this section, but it's worth a one-sentence mention as the third capability of the Lake-First architecture. Replay rehydrates historical full-fidelity data from Lake back through Stream pipelines to *any* destination — the mechanism for zero-risk vendor migrations. Point at it; don't demo it live.

**Takeaway**: "Lake-First with Search + Lakehouse means you never had to choose. Honeycomb shows you the pattern. Cribl Search shows you the smoking gun. Together they give you everything — at the cost shape you actually want."

---

# Section 8 — Capstone: build your own Cribl Pack (20 min)

**Goal**: integrate everything they've built into a portable, shareable artifact they can take back to their org.

## What's a Pack? (3 min)

A Cribl Pack is a versioned bundle of pipelines, routes, lookups, sample data, and knowledge objects — exportable as a `.crbl` file. Packs are:

- Portable across Cribl workspaces
- Shareable with teammates and on the [Cribl Pack Dispensary](https://packs.cribl.io)
- Versioned (semver) and dependency-aware
- The unit of "I built something useful, here's how to deploy it"

Note: there are **two flavors** of Pack in this workshop. Attendees consumed the workshop **Search Pack** in Section 7 (pre-built KQL queries). Now they'll author a **Stream Pack** — pre-built pipelines and routes.

## The exercise (15 min)

Each attendee builds a Stream Pack named `<their-initials>-otel-workshop` containing **at least**:

1. **Pipelines**:
   - `llm-cost-metrics` (from Section 5)
   - `llm-traces-to-honeycomb` (from Section 6)
   - At least one cardinality-control pipeline (from Section 2)
   - **Bonus**: the vendor-cost-estimation pipeline from Section 4 Demo 2
2. **Lookups**:
   - `service-owners.csv` (from Section 4 Demo 1)
   - `cloud-costs.csv` (from Section 4 Demo 2)
3. **Sample data**:
   - A captured set of LLM spans they can replay against the Pack offline
4. **README**:
   - One paragraph: what the Pack does, what it requires, what destinations it expects

Walkthrough on stage: how to create the Pack in Cribl UI, move pipelines into it, attach the lookup, capture sample data, fill out the manifest, and export.

## Share-out (2 min)

Three volunteers demo their Pack name + one thing they'd improve. Collect Pack files in a shared folder.

**Takeaway**: "You came in with telemetry pain. You're leaving with two Packs — the Search Pack you ran today, and a Stream Pack you authored yourself. Both are deployable. Both are stories you can tell. Both prove the pattern scales."

---

# Wrap-up

What attendees take home:

1. **The 3-layer mental model** (source / router / destination) and why it matters
2. **A working OTel + Cribl + Honeycomb + Grafana + Datadog + Lake stack** they can run on their laptop
3. **Two Packs** — the workshop Search Pack they ran, and a Stream Pack they authored
4. **A repeatable migration roadmap** — Lake-First, route-then-shape, vendor-switch via Replay
5. **Tail sampling at two layers** (OTel `tail_sampling` for in-memory, Cribl Lake + Search for in-storage) **and stream sampling at one** (Cribl Stream for logs and event streams) — three distinct tools for three distinct jobs
6. **Cost-as-a-metric** as a pattern they can apply to AI, requests, queries, anything
7. **KQL fluency** to ask cross-signal questions Lake → Search → answers in seconds

## Suggested next steps for attendees

- Bring up Cribl Stream against one real production source in a non-prod environment
- Pick one expensive vendor; identify three pipeline shaping opportunities; run them in shadow mode
- Stand up Cribl Lake; route one full-fidelity stream to it; enable Lakehouse on the high-volume datasets
- Author your first internal Search Pack with three KQL queries your team asks weekly
- Author your first internal Stream Pack; share it on your company's Cribl Pack Dispensary

---

## Presenter notes

- Total session: 180 minutes including one break.
- Sections 5–8 are the headline content. If you fall behind, compress Sections 1–4 first.
- Demos assume the workshop stack is running with all four signals visible in Live Capture, the Search Pack pre-loaded, and a Cribl Lake dataset receiving full fidelity from a Route configured before the workshop.
- The "Build a Pack" capstone is the time-sensitive close — protect the full 20 minutes.
- For Section 7, have at least 1 hour of Lake data accumulated before the workshop so the queries return meaningful results immediately. (If Lakehouse acceleration is enabled on the dataset, queries will be sub-second; otherwise expect 10–30s on first runs.)
- The EKS / real Honeycomb dataset can be referenced any time you want to show "this pattern on real data" instead of synthetic.

## Further reading for presenters

- [Mastering Tail Sampling for OpenTelemetry](https://cribl.io/blog/mastering-tail-sampling-for-opentelemetry-cost-effective-strategies-with-cribl/) — Patrick Wade's Lake-First tail-sampling walkthrough; the basis for the Section 7 scheduled-search demo.
- [Optimizing APM Costs and Visibility](https://cribl.io/blog/optimizing-apm-costs-and-visibility-with-cribl-stream-and-search/) — Scott Beamish's APM optimization article; the basis for the Section 7 alert-driven Search pivot demo.
- [Cribl Search documentation](https://docs.cribl.io/search/search-your-data/) — KQL reference, Lakehouse engine setup, scheduled-search configuration.
