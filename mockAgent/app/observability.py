from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.config import Settings


LOGGER_NAME = "accessible_travel_assistant"
logger = logging.getLogger(LOGGER_NAME)
_configured = False


def setup_observability(app: FastAPI, settings: Settings) -> None:
    """Configure stdout logs, OpenTelemetry traces, and optional OTLP log export.

    Heroku captures stdout/stderr automatically. When OTEL_EXPORTER_OTLP_ENDPOINT is
    configured, traces and logs are also exported to an OpenTelemetry collector or
    vendor endpoint using OTLP/HTTP.
    """

    global _configured
    if _configured:
        return

    _configure_stdlib_logging(settings.log_level)

    if settings.otel_enabled:
        _configure_opentelemetry(app, settings)

    _configured = True
    logger.info(
        "observability_configured",
        extra={
            "otel_enabled": settings.otel_enabled,
            "otel_endpoint_configured": bool(settings.otel_exporter_otlp_endpoint),
            "service_name": settings.otel_service_name,
            "environment": settings.otel_environment,
        },
    )


def add_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_http_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            if not request.url.path.startswith(("/assets/", "/logos/")):
                logger.info(
                    "http_request",
                    extra={
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "http_status_code": status_code,
                        "duration_ms": elapsed_ms,
                    },
                )


def _configure_stdlib_logging(log_level: str) -> None:
    level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _configure_opentelemetry(app: FastAPI, settings: Settings) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.exception("opentelemetry_import_failed")
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.otel_environment,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    if settings.otel_exporter_otlp_endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=_signal_endpoint(settings.otel_exporter_otlp_endpoint, "v1/traces"),
                    headers=_parse_headers(settings.otel_exporter_otlp_headers),
                )
            )
        )
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    if settings.otel_exporter_otlp_endpoint:
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=_signal_endpoint(settings.otel_exporter_otlp_endpoint, "v1/logs"),
                    headers=_parse_headers(settings.otel_exporter_otlp_headers),
                )
            )
        )
    set_logger_provider(logger_provider)

    logging.getLogger().addHandler(
        LoggingHandler(
            level=getattr(logging, settings.log_level, logging.INFO),
            logger_provider=logger_provider,
        )
    )

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    HTTPXClientInstrumentor().instrument()


def _parse_headers(raw_headers: str | None) -> dict[str, str] | None:
    if not raw_headers:
        return None

    headers: dict[str, str] = {}
    for item in raw_headers.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers or None


def _signal_endpoint(base_endpoint: str, signal_path: str) -> str:
    endpoint = base_endpoint.rstrip("/")
    if endpoint.endswith(("/v1/traces", "/v1/logs", "/v1/metrics")):
        return endpoint
    return f"{endpoint}/{signal_path}"
