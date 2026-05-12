#!/usr/bin/env python3
"""Synthetic OpenTelemetry GenAI telemetry generator.

Emits LLM-shaped spans following the OpenTelemetry GenAI semantic conventions
(https://opentelemetry.io/docs/specs/semconv/gen-ai) to an OTLP/gRPC endpoint.

Used in the Cribl / Honeycomb Workshop to demo routing, masking, and shaping
of AI/LLM telemetry without paying for real LLM API calls.

The span shape mirrors what OpenLLMetry and OpenLIT emit in production today,
so anything you build against this generator will work against real LLM
instrumentation. Prompts intentionally include obvious test-data PII patterns
(Stripe test card 4242..., reserved 555 phone area code, the well-known invalid
SSN 123-45-6789) so attendees can demo Cribl Mask functions on synthetic data
that is universally recognized as fake.
"""

import logging
import os
import random
import time
import uuid

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("genaitelgen")

OTLP_ENDPOINT = os.environ.get("OTLP_ENDPOINT", "otel-collector:4317")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "workshop-ai-assistant")
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "1.0.0")
DEPLOYMENT_ENV = os.environ.get("DEPLOYMENT_ENV", "production")
RATE_PER_SEC = float(os.environ.get("RATE_PER_SEC", "2"))

# Models with rough public list pricing in USD per 1M tokens. Weights bias the
# random selection so the cost story has a realistic mix of cheap and pricey.
MODELS = [
    {"system": "openai",      "model": "gpt-4o",            "in_per_m": 2.50, "out_per_m": 10.00, "weight": 3},
    {"system": "openai",      "model": "gpt-4o-mini",       "in_per_m": 0.15, "out_per_m": 0.60,  "weight": 5},
    {"system": "anthropic",   "model": "claude-3-5-sonnet", "in_per_m": 3.00, "out_per_m": 15.00, "weight": 3},
    {"system": "anthropic",   "model": "claude-3-haiku",    "in_per_m": 0.25, "out_per_m": 1.25,  "weight": 4},
    {"system": "aws.bedrock", "model": "claude-3-5-sonnet", "in_per_m": 3.00, "out_per_m": 15.00, "weight": 1},
]
MODEL_WEIGHTS = [m["weight"] for m in MODELS]

ROUTES = ["summarize-email", "code-review", "support-chat", "doc-qa", "agent-tool-call"]
USERS  = ["alice@example.com", "bob@example.com", "carol@example.com", "dave@example.com"]
TOOLS  = ["weather_lookup", "calendar_search", "kb_query", "send_email", "code_execute"]

PROMPTS = [
    "Summarize this email from the customer success team about Q3 renewals.",
    "Why is my React component re-rendering on every state change?",
    "What's the refund policy for an order placed last week?",
    "Translate this product description to Spanish.",
    "Help me debug this Python traceback: KeyError: 'user_id'",
    "Customer Alice (alice@example.com, card 4242 4242 4242 4242) needs a refund.",
    "Lookup account for SSN 123-45-6789 and reset their password.",
    "Generate a draft response to support ticket #4892.",
    "Explain how OAuth 2.0 device authorization flow works.",
    "Phone number 555-0100 left a voicemail asking for a callback.",
]
COMPLETIONS = [
    "Here's a summary of the email thread covering renewal commits, expansion opportunities, and at-risk accounts...",
    "The component re-renders because you're creating a new object reference each render. Use useMemo to memoize...",
    "Our refund policy allows returns within 30 days of purchase, provided the item is in original condition...",
    "Aquí está la descripción del producto traducida al español...",
    "The KeyError occurs because the dictionary doesn't contain a 'user_id' key. Add a check with .get()...",
    "I cannot process payment card or SSN information directly. Please escalate this to a human agent.",
    "I'm not able to access account information or perform authentication-related actions.",
    "Draft response: Thank you for reaching out. We've received your ticket and will respond within 24 hours...",
    "OAuth 2.0 device authorization flow is designed for devices with limited input capabilities, like smart TVs...",
    "I'll log a callback request for the provided phone number.",
]

# Heavy bias toward "stop"; occasional "length" (truncated) and "content_filter"
# (refused) outcomes give attendees something to filter and tail-sample on.
FINISH_REASONS = ["stop"] * 8 + ["length", "content_filter"]


def setup_tracer() -> trace.Tracer:
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "deployment.environment": DEPLOYMENT_ENV,
    })
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("genaitelgen")


def emit_one(tracer: trace.Tracer) -> None:
    """Emit one realistic LLM request as a small parent/child trace.

    Span tree (matches what OpenLLMetry / OpenLIT produce in production):

        SERVER  POST /api/v1/chat/<route>
        ├── CLIENT  embedding text-embedding-3-small   (~30% of requests)
        ├── CLIENT  chat <model>                        (always — the LLM call)
        └── CLIENT  execute_tool <tool_name>            (~10% of requests, no errors)
    """
    model = random.choices(MODELS, weights=MODEL_WEIGHTS, k=1)[0]
    route = random.choice(ROUTES)
    user = random.choice(USERS)

    idx = random.randrange(len(PROMPTS))
    prompt = PROMPTS[idx]
    completion = COMPLETIONS[idx]
    finish = random.choice(FINISH_REASONS)

    input_tokens = random.randint(50, 2000)
    output_tokens = (
        random.randint(3500, 4096) if finish == "length" else random.randint(100, 3000)
    )
    cost = (input_tokens / 1_000_000) * model["in_per_m"] + (output_tokens / 1_000_000) * model["out_per_m"]

    # LLM-call latency loosely scales with output tokens, with a 2% chance of a
    # slow tail (15-30s) so tail-sampling and latency filtering have something
    # to find.
    llm_base_ms = 200 + output_tokens * 0.5
    llm_latency_ms = llm_base_ms * random.uniform(0.7, 1.6)
    if random.random() < 0.02:
        llm_latency_ms += random.uniform(15000, 30000)

    is_error = random.random() < 0.03
    has_embedding = random.random() < 0.30
    has_tool_call = (not is_error) and (random.random() < 0.10)

    embedding_ms = random.uniform(20, 80) if has_embedding else 0.0
    tool_ms = random.uniform(50, 500) if has_tool_call else 0.0
    overhead_ms = random.uniform(10, 50)
    total_ms = embedding_ms + llm_latency_ms + tool_ms + overhead_ms

    # Roll all timestamps so the parent's end_time lands at "now". Honeycomb
    # and most backends drop events with future timestamps.
    parent_end_ns = time.time_ns()
    parent_start_ns = parent_end_ns - int(total_ms * 1_000_000)
    cursor = parent_start_ns + int(overhead_ms / 2 * 1_000_000)

    parent = tracer.start_span(
        f"POST /api/v1/chat/{route}",
        kind=SpanKind.SERVER,
        start_time=parent_start_ns,
    )
    try:
        parent.set_attribute("http.request.method", "POST")
        parent.set_attribute("http.route", f"/api/v1/chat/{route}")
        parent.set_attribute("http.response.status_code", 500 if is_error else 200)
        parent.set_attribute("app.route", route)
        parent.set_attribute("app.user", user)

        ctx = trace.set_span_in_context(parent)

        if has_embedding:
            emb_start_ns = cursor
            emb_end_ns = emb_start_ns + int(embedding_ms * 1_000_000)
            emb_span = tracer.start_span(
                "embedding text-embedding-3-small",
                kind=SpanKind.CLIENT,
                context=ctx,
                start_time=emb_start_ns,
            )
            emb_span.set_attribute("gen_ai.system", "openai")
            emb_span.set_attribute("gen_ai.operation.name", "embeddings")
            emb_span.set_attribute("gen_ai.request.model", "text-embedding-3-small")
            emb_span.set_attribute("gen_ai.usage.input_tokens", random.randint(20, 200))
            emb_span.set_status(Status(StatusCode.OK))
            emb_span.end(end_time=emb_end_ns)
            cursor = emb_end_ns

        llm_start_ns = cursor
        llm_end_ns = llm_start_ns + int(llm_latency_ms * 1_000_000)
        llm_span = tracer.start_span(
            f"chat {model['model']}",
            kind=SpanKind.CLIENT,
            context=ctx,
            start_time=llm_start_ns,
        )
        llm_span.set_attribute("gen_ai.system", model["system"])
        llm_span.set_attribute("gen_ai.operation.name", "chat")
        llm_span.set_attribute("gen_ai.request.model", model["model"])
        llm_span.set_attribute("gen_ai.request.temperature", round(random.uniform(0.0, 1.0), 2))
        llm_span.set_attribute("gen_ai.request.max_tokens", 4096)
        llm_span.set_attribute("gen_ai.request.top_p", 1.0)

        llm_span.set_attribute("gen_ai.response.id", f"chatcmpl-{uuid.uuid4().hex[:24]}")
        llm_span.set_attribute("gen_ai.response.model", model["model"])
        llm_span.set_attribute("gen_ai.response.finish_reasons", [finish])

        llm_span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        llm_span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
        llm_span.set_attribute("gen_ai.usage.total_tokens", input_tokens + output_tokens)
        llm_span.set_attribute("gen_ai.usage.cost", round(cost, 6))

        # OpenLLMetry-style prompt/completion attributes — what production OTel
        # LLM instrumentations emit today and the natural target for Cribl Mask
        # functions in the workshop's PII-redaction demo.
        llm_span.set_attribute("gen_ai.prompt.0.role", "user")
        llm_span.set_attribute("gen_ai.prompt.0.content", prompt)
        llm_span.set_attribute("gen_ai.completion.0.role", "assistant")
        llm_span.set_attribute("gen_ai.completion.0.content", completion)
        llm_span.set_attribute("gen_ai.completion.0.finish_reason", finish)

        llm_span.set_attribute("app.route", route)
        llm_span.set_attribute("app.user", user)

        if is_error:
            llm_span.set_status(Status(StatusCode.ERROR, "rate_limit_exceeded"))
            llm_span.set_attribute("error.type", "rate_limit_exceeded")
        else:
            llm_span.set_status(Status(StatusCode.OK))
        llm_span.end(end_time=llm_end_ns)
        cursor = llm_end_ns

        if has_tool_call:
            tool_name = random.choice(TOOLS)
            tool_start_ns = cursor
            tool_end_ns = tool_start_ns + int(tool_ms * 1_000_000)
            tool_span = tracer.start_span(
                f"execute_tool {tool_name}",
                kind=SpanKind.CLIENT,
                context=ctx,
                start_time=tool_start_ns,
            )
            tool_span.set_attribute("gen_ai.operation.name", "execute_tool")
            tool_span.set_attribute("gen_ai.tool.name", tool_name)
            tool_span.set_attribute("gen_ai.tool.type", "function")
            tool_span.set_status(Status(StatusCode.OK))
            tool_span.end(end_time=tool_end_ns)

        if is_error:
            parent.set_status(Status(StatusCode.ERROR, "llm_call_failed"))
            parent.set_attribute("error.type", "rate_limit_exceeded")
        else:
            parent.set_status(Status(StatusCode.OK))
    finally:
        parent.end(end_time=parent_end_ns)


def main() -> None:
    log.info("genaitelgen → %s @ %.2f spans/sec (service=%s)", OTLP_ENDPOINT, RATE_PER_SEC, SERVICE_NAME)
    tracer = setup_tracer()
    interval = 1.0 / RATE_PER_SEC
    while True:
        loop_start = time.time()
        try:
            emit_one(tracer)
        except Exception:
            log.exception("emit failed")
        elapsed = time.time() - loop_start
        time.sleep(max(0.0, interval - elapsed))


if __name__ == "__main__":
    main()
