import logging
import time
from contextlib import contextmanager
from typing import Iterator

import structlog
from prometheus_client import Counter, Histogram

from agent_yhzh.config import settings


HTTP_REQUESTS = Counter(
    "agent_yhzh_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "agent_yhzh_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
LEARNING_EVENTS = Counter(
    "agent_yhzh_learning_events_total",
    "Learning pipeline events",
    ["status", "event_type"],
)
RETRIEVAL_REQUESTS = Counter(
    "agent_yhzh_retrieval_requests_total",
    "Knowledge retrieval requests",
    ["result"],
)
IMPORT_JOBS = Counter(
    "agent_yhzh_import_jobs_total",
    "Document import jobs",
    ["status"],
)


def configure_logging() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("agent_yhzh")


def configure_tracing(app, engine) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.app_name})
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            )
        )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception as error:
        logger.warning("tracing_initialization_failed", error=str(error))


@contextmanager
def timed_operation(name: str, **context) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        logger.info(
            "operation_completed",
            operation=name,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            **context,
        )
