import contextlib
import logging
from typing import Any

from opentelemetry import trace

__all__ = ("extract_opentelemetry_trace_meta",)


def extract_opentelemetry_trace_meta(
    wrapped_logger: logging.Logger | None,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    with contextlib.suppress(KeyError, ValueError):
        span = trace.get_current_span()
        if not span.is_recording():
            return event_dict

        ctx = span.get_span_context()
        service_name = trace.get_tracer_provider().resource.attributes["service.name"]  # type: ignore[attr-defined]
        parent = getattr(span, "parent", None)

        event_dict["span_id"] = trace.format_span_id(ctx.span_id)
        event_dict["trace_id"] = trace.format_trace_id(ctx.trace_id)
        event_dict["service.name"] = service_name

        if parent:
            event_dict["parent_span_id"] = trace.format_span_id(parent.span_id)

    return event_dict
