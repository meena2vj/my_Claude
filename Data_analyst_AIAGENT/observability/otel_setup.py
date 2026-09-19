"""OpenTelemetry setup -- one cached `TracerProvider`. With no
`OTEL_EXPORTER_OTLP_ENDPOINT` configured (the HF Spaces-safe default), spans
are created but exported nowhere -- they still flow through `start_span`,
which is the single instrumentation point nodes/tools/LLM calls use, so
turning on real export later needs no call-site changes.
"""

from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from config.logging_config import get_logger
from config.settings import OTEL_EXPORTER_OTLP_ENDPOINT

logger = get_logger(__name__)

_provider: TracerProvider | None = None


def get_tracer_provider() -> TracerProvider:
    global _provider
    if _provider is not None:
        return _provider

    provider = TracerProvider(resource=Resource.create({"service.name": "data-analyst-ai-agent"}))

    if OTEL_EXPORTER_OTLP_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT))
            )
        except ImportError:
            logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT is set but the OTLP exporter package "
                            "is not installed; spans will not be exported.")

    trace.set_tracer_provider(provider)
    _provider = provider
    return _provider


def get_tracer():
    return trace.get_tracer("data-analyst-ai-agent", tracer_provider=get_tracer_provider())


@contextmanager
def start_span(name: str, **attributes):
    with get_tracer().start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
