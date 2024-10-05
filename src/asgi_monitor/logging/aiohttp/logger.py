import contextlib
import logging
from typing import TYPE_CHECKING, Any

from aiohttp.web_log import AccessLogger
from aiohttp.web_request import BaseRequest
from aiohttp.web_response import StreamResponse
from opentelemetry import trace

if TYPE_CHECKING:
    from opentelemetry.trace import Span

__all__ = ("TraceAccessLogger",)


class TraceAccessLogger(AccessLogger):
    """
    The heir of the default logging AccessLogger class,
    which implements the addition of trace meta information to the aiohttp request log.
    """

    def log(self, request: BaseRequest, response: StreamResponse, time: float) -> None:
        if not self.logger.isEnabledFor(logging.INFO):
            # Avoid formatting the log line if it will not be emitted.
            return
        try:
            fmt_info = self._format_line(request, response, time)

            values = []
            extra: dict[str, Any] = {}
            for key, value in fmt_info:
                values.append(value)

                if key.__class__ is str:
                    extra[key] = value
                else:
                    k1, k2 = key  # type: ignore[misc]
                    dct = extra.get(k1, {})  # type: ignore[has-type]
                    dct[k2] = value  # type: ignore[has-type]
                    extra[k1] = dct  # type: ignore[has-type]

            with contextlib.suppress(KeyError, ValueError):
                span: Span = request.span  # type: ignore[attr-defined]
                ctx = span.get_span_context()
                service_name = trace.get_tracer_provider().resource.attributes["service.name"]  # type: ignore[attr-defined]
                parent = getattr(span, "parent", None)

                extra["span_id"] = trace.format_span_id(ctx.span_id)
                extra["trace_id"] = trace.format_trace_id(ctx.trace_id)
                extra["service.name"] = service_name

                if parent:
                    extra["parent_span_id"] = trace.format_span_id(parent.span_id)

            self.logger.info(self._log_format % tuple(values), extra=extra)
        except Exception:
            self.logger.exception("Error in logging")
