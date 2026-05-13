#!/usr/bin/env python3
"""
Workshop Synthetic Log Generator — fixed version
Uses LoggingHandler per service so we never call set_logger_provider()
more than once per service, avoiding the "Overriding not allowed" error.
"""

import os
import random
import time
import logging

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# ── Config from environment ────────────────────────────────────────────────────

ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
RATE     = float(os.getenv("LOG_RATE_EPS", "2"))
SERVICE  = os.getenv("SERVICE_NAME", None)
INSECURE = os.getenv("OTEL_INSECURE", "false").lower() in ("true", "1", "yes")

# ── Scenario data ──────────────────────────────────────────────────────────────

USERS = [
    {"email": "alice@example.com",   "phone": "555-867-5309", "id": "usr_a1b2c3"},
    {"email": "bob@example.com",     "phone": "555-234-5678", "id": "usr_d4e5f6"},
    {"email": "charlie@example.com", "phone": "555-345-6789", "id": "usr_g7h8i9"},
    {"email": "dave@example.com",    "phone": "555-456-7890", "id": "usr_j1k2l3"},
    {"email": "eve@example.com",     "phone": "555-567-8901", "id": "usr_m4n5o6"},
]

CARDS = [
    "4532015112830366",
    "5425233430109903",
    "374251018720955",
    "6011111111111117",
]

ROUTES   = ["code-review", "summarize-email", "agent-tool-call", "data-analysis"]
MODELS   = ["gpt-4o-mini", "gpt-4o", "claude-3-haiku"]
SERVICES = [
    "workshop-ai-assistant",
    "workshop-checkout",
    "workshop-order-service",
    "workshop-notification",
]

# ── Scenario generators ────────────────────────────────────────────────────────

def scenario_http_request(user):
    route    = random.choice(ROUTES)
    duration = random.randint(80, 3500)
    status   = random.choices([200, 422, 429, 500], weights=[85, 6, 5, 4])[0]
    severity = "INFO" if status < 400 else "WARN" if status < 500 else "ERROR"
    return {
        "body": f"POST /api/v1/chat/{route} {status} {duration}ms user={user['email']}",
        "severity": severity,
        "attributes": {
            "http.method":      "POST",
            "http.route":       f"/api/v1/chat/{route}",
            "http.status_code": status,
            "http.duration_ms": duration,
            "app.user":         user["email"],
            "app.user_id":      user["id"],
            "app.route":        route,
        },
    }

def scenario_llm_call(user):
    model         = random.choice(MODELS)
    input_tokens  = random.randint(200, 2000)
    output_tokens = random.randint(100, 3000)
    cost          = round((input_tokens * 0.00000015) + (output_tokens * 0.0000006), 6)
    route         = random.choice(ROUTES)
    return {
        "body": f"LLM call completed model={model} input_tokens={input_tokens} output_tokens={output_tokens} cost=${cost:.4f} user={user['email']}",
        "severity": "INFO",
        "attributes": {
            "gen_ai.system":              "openai",
            "gen_ai.operation.name":      "chat",
            "gen_ai.request.model":       model,
            "gen_ai.response.model":      model,
            "gen_ai.usage.input_tokens":  input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
            "gen_ai.usage.total_tokens":  input_tokens + output_tokens,
            "gen_ai.usage.cost":          cost,
            "app.user":                   user["email"],
            "app.route":                  route,
        },
    }

def scenario_pii_callback(user):
    return {
        "body": f"Callback request received phone={user['phone']} account={user['id']} user={user['email']}",
        "severity": "INFO",
        "attributes": {
            "app.user":    user["email"],
            "app.user_id": user["id"],
            "event.type":  "callback_request",
            "app.channel": "voicemail",
        },
    }

def scenario_pii_payment(user):
    card   = random.choice(CARDS)
    amount = round(random.uniform(9.99, 299.99), 2)
    status = random.choices(["approved", "declined"], weights=[85, 15])[0]
    return {
        "body": f"Payment {status}: card={card} amount=${amount} user={user['email']} phone={user['phone']}",
        "severity": "INFO" if status == "approved" else "WARN",
        "attributes": {
            "app.user":       user["email"],
            "app.user_id":    user["id"],
            "payment.status": status,
            "payment.amount": amount,
            "payment.method": "card",
        },
    }

def scenario_rate_limit(user):
    route = random.choice(ROUTES)
    return {
        "body": f"Rate limit exceeded user={user['email']} route={route} retry_after=60s",
        "severity": "WARN",
        "attributes": {
            "app.user":         user["email"],
            "app.user_id":      user["id"],
            "app.route":        route,
            "error.type":       "rate_limit",
            "http.status_code": 429,
            "retry_after_s":    60,
        },
    }

def scenario_llm_timeout(user):
    model     = random.choice(MODELS)
    timeout_s = random.choice([15, 20, 30])
    return {
        "body": f"LLM request timed out model={model} timeout={timeout_s}s user={user['email']}",
        "severity": "ERROR",
        "attributes": {
            "gen_ai.system":         "openai",
            "gen_ai.request.model":  model,
            "error.type":            "timeout",
            "error.timeout_seconds": timeout_s,
            "app.user":              user["email"],
            "app.user_id":           user["id"],
        },
    }

def scenario_session_lifecycle(user):
    event    = random.choice(["session_started", "session_ended", "session_expired"])
    severity = "INFO" if event != "session_expired" else "WARN"
    return {
        "body": f"User {event} user={user['email']} session_id=sess_{user['id'][-6:]}",
        "severity": severity,
        "attributes": {
            "app.user":    user["email"],
            "app.user_id": user["id"],
            "event.type":  event,
            "session.id":  f"sess_{user['id'][-6:]}",
        },
    }

def scenario_order(user):
    order_id = f"ord_{random.randint(100000, 999999)}"
    items    = random.randint(1, 5)
    total    = round(random.uniform(19.99, 499.99), 2)
    status   = random.choices(["created", "processing", "failed"], weights=[70, 25, 5])[0]
    card     = random.choice(CARDS)
    return {
        "body": f"Order {status} order_id={order_id} items={items} total=${total} user={user['email']} card={card}",
        "severity": "ERROR" if status == "failed" else "INFO",
        "attributes": {
            "app.user":     user["email"],
            "app.user_id":  user["id"],
            "order.id":     order_id,
            "order.status": status,
            "order.items":  items,
            "order.total":  total,
        },
    }

# ── Scenario weights ───────────────────────────────────────────────────────────

SCENARIOS = [
    (scenario_http_request,      30),
    (scenario_llm_call,          25),
    (scenario_pii_callback,      10),
    (scenario_pii_payment,       10),
    (scenario_session_lifecycle, 10),
    (scenario_order,             10),
    (scenario_rate_limit,         3),
    (scenario_llm_timeout,        2),
]

SCENARIO_FNS, SCENARIO_WEIGHTS = zip(*SCENARIOS)

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO":  logging.INFO,
    "WARN":  logging.WARNING,
    "ERROR": logging.ERROR,
}

# ── One logger per service — created once, reused forever ─────────────────────
# Fix: LoggingHandler(logger_provider=provider) instead of
# set_logger_provider() which can only be called once globally.

_loggers: dict = {}

def get_logger(service_name: str) -> logging.Logger:
    if service_name in _loggers:
        return _loggers[service_name]

    resource = Resource.create({
        "service.name":           service_name,
        "service.version":        "2.0.0",
        "deployment.environment": "production",
        "workshop.source":        "telemetrygen-laptop",
    })

    exporter = OTLPLogExporter(endpoint=ENDPOINT, insecure=INSECURE)
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    # Attach handler to this specific provider — no global override
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)

    logger = logging.getLogger(f"workshop.{service_name}")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # don't bubble up to root logger

    _loggers[service_name] = logger
    return logger

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    tls_status = "disabled (insecure)" if INSECURE else "enabled"
    print(f"Workshop log generator starting")
    print(f"  Endpoint : {ENDPOINT}")
    print(f"  Rate     : {RATE} events/sec")
    print(f"  Service  : {SERVICE or 'rotating across all workshop services'}")
    print(f"  TLS      : {tls_status}")
    print()

    # Pre-create all loggers at startup
    services_to_init = [SERVICE] if SERVICE else SERVICES
    for svc in services_to_init:
        get_logger(svc)
    print(f"  Loggers  : {len(services_to_init)} service(s) initialised")
    print()

    interval = 1.0 / RATE
    count    = 0

    try:
        while True:
            user     = random.choice(USERS)
            svc      = SERVICE or random.choice(SERVICES)
            scenario = random.choices(SCENARIO_FNS, weights=SCENARIO_WEIGHTS)[0]
            event    = scenario(user)

            logger = get_logger(svc)
            level  = LEVEL_MAP.get(event["severity"], logging.INFO)

            # extra= fields become OTel log record attributes via LoggingHandler
            logger.log(level, event["body"], extra=event["attributes"])
            count += 1

            if count % 10 == 0:
                print(f"[{count:>6}] {event['severity']:<5} {svc:<35} {event['body'][:65]}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\nStopped after {count} events")

if __name__ == "__main__":
    main()
