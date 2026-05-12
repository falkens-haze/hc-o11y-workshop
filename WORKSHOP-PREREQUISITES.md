---
title: "Workshop Prerequisites"
subtitle: "Decoupling Observability with OpenTelemetry, Cribl Stream, and Honeycomb"
author: "Greg Coleman, Technical Alliances Engineer · gcoleman@cribl.io"
date: "May 20, 2026"
document-version: "1.0"
classification: "Workshop Attendees — Internal Use"
geometry: "margin=1in"
---

# Workshop Prerequisites

**Decoupling Observability with OpenTelemetry, Cribl Stream, and Honeycomb**

---

| Field              | Value                                                              |
| ------------------ | ------------------------------------------------------------------ |
| Workshop date      | May 20, 2026                                                       |
| Duration           | 3 hours (includes one 10-minute break)                             |
| Audience           | Architects and engineering leaders responsible for observability   |
| Format             | Hands-on, laptop-based                                             |
| Document version   | 1.0                                                                |
| Issue date         | _to be completed_                                                  |
| Prepared by        | Greg Coleman, Technical Alliances Engineer, Cribl                  |
| Contact            | gcoleman@cribl.io                                                  |

---

## 1. Purpose

This document lists everything you need to have in place **before** the workshop begins on May 20, 2026. Most steps require account creation, identity verification, or trial provisioning — none of which can be rushed on the day of the workshop. Please complete the steps below **at least 48 hours in advance** so that we can resolve any access issues before the session.

If any step is blocked or unclear, contact Greg Coleman at the address above and we will work through it together.

---

## 2. What you will be doing in the workshop

You will run a working three-layer observability stack on your laptop:

> **Telemetry sources** (synthetic OpenTelemetry traces, metrics, logs, and LLM spans) → **Cribl Stream** (the router, running in your own Cribl Cloud workspace) → **observability destinations** (Honeycomb plus one or more destinations of your choosing).

By the end of the workshop you will have authored a Cribl Stream **Pack** — a portable, versioned bundle of pipelines, lookups, and routes — that you can take back to your own organization.

To make that work, you need a few things ready before you arrive.

---

## 3. Required hardware and software

| Item                            | Detail                                                                           |
| ------------------------------- | -------------------------------------------------------------------------------- |
| Laptop                          | macOS, Linux, or Windows with WSL2                                               |
| RAM                             | 8 GB minimum, 16 GB recommended                                                  |
| Disk                            | 5 GB free for container images and lake data                                     |
| Docker Desktop                  | Version 28.x or later (tested with 28.2.2)                                       |
| Network                         | Standard internet access; HTTPS outbound to `*.cribl.cloud` and chosen destinations |
| Terminal                        | Any modern shell (`zsh`, `bash`, PowerShell + WSL)                               |
| Browser                         | Current Chrome, Firefox, Safari, or Edge for the Cribl UI                        |

> **Note**: corporate-managed laptops with restrictive outbound proxies have caused issues in past workshops. If your environment blocks outbound HTTPS to arbitrary subdomains, please flag this in advance.

---

## 4. Required accounts and access

You will need **four** things provisioned before workshop day. The first one gates the others, so please start there.

### 4.1 Cribl Cloud workspace (required — start here)

You will need your own Cribl Cloud workspace. The free tier is sufficient for the workshop, and after you invite Greg as an administrator he will upgrade your workspace to **Enterprise** for the duration of the workshop so that all features used in the curriculum (Cribl Stream, Cribl Lake, Cribl Search, Lakehouse engines) are available to you.

**Step-by-step instructions:**

> _The full activation and invitation procedure will be added by Greg before this document is distributed. Placeholder for:_
>
> _- How to register a Cribl Cloud organization at https://cribl.cloud/_
> _- How to verify your email and complete onboarding_
> _- How to invite `gcoleman@cribl.io` as an Admin on your organization_
> _- How to confirm the Enterprise upgrade once Greg has applied it_

Once you have invited `gcoleman@cribl.io` and confirmation comes back that your workspace has been upgraded to Enterprise, Greg will send you the link to the **workshop code repository**. The repository contains the synthetic telemetry generators, the OTel Collector configuration, and the launch script you will run on the workshop day.

> **Important**: please do not skip the invitation step. The Enterprise upgrade is what enables Cribl Lake, Cribl Search, and Lakehouse engines, all of which are core to the workshop. Without it, several sections will not work end-to-end on your workspace.

### 4.2 Honeycomb account (required)

Honeycomb is the trace destination featured in this workshop and is required for the partner-integration sections of the curriculum.

| Step | Action                                                                                 |
| ---- | -------------------------------------------------------------------------------------- |
| 1    | Visit [https://www.honeycomb.io/](https://www.honeycomb.io/) and sign up for a free account |
| 2    | Complete email verification                                                            |
| 3    | Create a Honeycomb **environment** (the free tier provides one by default)             |
| 4    | Generate an **API key** for that environment and save it somewhere secure              |
| 5    | Confirm you can log in and reach the **Environments → API Keys** screen                |

The free tier is sufficient. No credit card is required.

### 4.3 At least one additional destination (required)

The workshop's core teaching pattern is **routing one signal stream to multiple destinations through Cribl Stream**. To experience this end-to-end, you need at least one additional destination beyond Honeycomb. Two destinations is recommended; three (the workshop's full reference architecture) is the stretch goal.

**Recommended default — Grafana Cloud (free tier):**

> Sign up at [https://grafana.com/products/cloud/](https://grafana.com/products/cloud/) and provision a free tier stack. Make a note of your **Prometheus remote-write URL** and **access token**. This pairs cleanly with the workshop's metrics demos and is the default referenced in the curriculum.

**Alternative — any Cribl-supported destination of your choice:**

If you would rather demonstrate Cribl's value against a destination you actually use day-to-day, you may substitute any destination from Cribl's supported list, **provided you have write credentials and the required permissions** as documented for that destination. See:

> [https://docs.cribl.io/stream/destinations/](https://docs.cribl.io/stream/destinations/)

Common substitutions that work well in the workshop:

| Signal     | Free-tier-friendly alternatives                                                 |
| ---------- | ------------------------------------------------------------------------------- |
| Metrics    | Grafana Cloud (Prometheus), New Relic, Datadog, Dynatrace, InfluxDB Cloud       |
| Logs       | Datadog, Grafana Cloud (Loki), Splunk Cloud trial, Elastic Cloud, Sumo Logic    |
| Traces     | Honeycomb (already required), Datadog APM, Grafana Cloud Tempo, Dynatrace OTLP  |
| Any signal | Cribl Lake (included with your Cribl Cloud workspace — no extra account needed) |

You are responsible for confirming that:

1. You can authenticate to your chosen destination (you have a valid API key, URL, or credentials).
2. Your account has **write** permission to ingest data, per the destination's own documentation linked from the Cribl Destinations page above.
3. Your free tier or trial period covers May 20, 2026.

### 4.4 Workshop code repository (provided after step 4.1)

Once your Cribl Cloud invitation lands in Greg's inbox, you will receive a link to the workshop code repository. Plan to:

1. Clone the repository to your laptop.
2. Read the included `README.md`.
3. Run `./start.sh` and confirm the synthetic telemetry stack starts cleanly.
4. Confirm in your Cribl Cloud OTel Source's **Live Capture** that data is arriving.

This dry-run takes about 10 minutes and is the single most reliable way to head off day-of issues.

---

## 5. Pre-workshop timeline

| When             | Action                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| **T - 7 days**   | Complete steps 4.1 (Cribl Cloud) and 4.2 (Honeycomb). Invite `gcoleman@cribl.io` to your workspace.   |
| **T - 5 days**   | Receive Enterprise upgrade confirmation and the workshop code repository link from Greg.              |
| **T - 3 days**   | Provision your additional destination(s) per step 4.3.                                                |
| **T - 2 days**   | Clone the repository, run `./start.sh`, and confirm data is flowing into Cribl Live Capture.          |
| **T - 1 day**    | Final connectivity check. Resolve any outstanding issues with Greg by end of business.                |
| **Workshop day** | Arrive 10 minutes early. Have your laptop, Cribl Cloud, Honeycomb, and destinations open and ready.   |

---

## 6. Day-of checklist

Bring this checklist with you. Each item should be a confirmed "yes" before the workshop begins.

- [ ] Docker Desktop is running on my laptop
- [ ] My Cribl Cloud workspace is active and shows the Enterprise badge
- [ ] `gcoleman@cribl.io` is listed as an Admin on my Cribl Cloud organization
- [ ] My Cribl Cloud OTel Source is created and reachable from my laptop
- [ ] My Honeycomb account is active and I have my API key ready
- [ ] My additional destination(s) are configured and I have write credentials in hand
- [ ] I have cloned the workshop code repository to my laptop
- [ ] I have run `./start.sh` at least once and confirmed data in Cribl Live Capture
- [ ] I know how to reach Greg if anything breaks during the session

---

## 7. Support and contact

For any prerequisite-related questions or blockers, contact:

**Greg Coleman**
Technical Alliances Engineer, Cribl
Email: gcoleman@cribl.io

When emailing, please include:

- Your name and organization
- The step number from this document (e.g., "Step 4.1") that is blocking you
- A brief description of the issue and any error messages you have seen
- Screenshots if applicable

Greg will reply within one business day. For issues encountered within 48 hours of the workshop, please flag the message as urgent.

---

## Appendix A — Why each prerequisite matters

For attendees who want to understand why each requirement is on the list:

| Prerequisite             | Why it matters for the workshop                                                                 |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| Docker Desktop           | Runs the synthetic OpenTelemetry source containers locally on your laptop                       |
| Cribl Cloud (Enterprise) | Hosts your Cribl Stream worker, Cribl Lake dataset, and Cribl Search workspace                  |
| Honeycomb                | Featured trace destination; powers the partner-integration sections of the curriculum           |
| Additional destination   | Demonstrates the multi-destination routing pattern that is core to the three-layer architecture |
| Workshop code repository | Provides the synthetic telemetry generators (traces, metrics, logs, LLM spans) and configs       |

---

## Appendix B — Document control

| Field            | Value                                                                  |
| ---------------- | ---------------------------------------------------------------------- |
| Document title   | Workshop Prerequisites — Decoupling Observability                      |
| Document version | 1.0                                                                    |
| Owner            | Greg Coleman, Technical Alliances Engineer, Cribl                      |
| Contact          | gcoleman@cribl.io                                                      |
| Distribution     | Confirmed workshop attendees only                                      |
| Review cycle     | Per workshop session                                                   |
| Next review      | May 19, 2026 (one day before workshop)                                 |

---

_End of document_
