from __future__ import annotations

import time
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from litestar import Request, Response, get
from litestar.enums import ScopeType
from litestar.middleware.base import AbstractMiddleware, DefineMiddleware
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.types import ASGIApp, Message, Receive, Scope, Send
    from prometheus_client import CollectorRegistry

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.metrics.manager import MetricsManager, build_metrics_manager
from asgi_monitor.tracing.config import BaseTracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware

__all__ = (
    "TracingConfig",
    "build_tracing_middleware",
    "MetricsConfig",
    "build_metrics_middleware",
    "add_metrics_endpoint",
)


def _get_default_span_details(scope: Scope) -> tuple[str, dict[str, Any]]:
    method = scope["method"]  # type: ignore[typeddict-item]  # The WebSocket is not supported
    path = scope["path_template"] if scope.get("path_template") else scope["path"]
    return f"{method} {path}", {SpanAttributes.HTTP_ROUTE: path}


@dataclass(slots=True, frozen=True)
class TracingConfig(BaseTracingConfig):
    """
    Configuration class for the OpenTelemetry middleware.
    Consult the OpenTelemetry ASGI documentation for more info about the configuration options.
    https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html
    """

    exclude_urls_env_key: str = "LITESTAR"
    """
    Key to use when checking whether a list of excluded urls is passed via ENV.
    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'.
    """

    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]] = _get_default_span_details
    """
    Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """


@dataclass(slots=True, frozen=True)
class MetricsConfig(BaseMetricsConfig):
    """Configuration class for the Metrics middleware."""

    metrics_prefix: str = "litestar"
    """The prefix to use for the metrics."""


class TracingMiddleware(AbstractMiddleware):
    __slots__ = ("app", "open_telemetry_middleware")

    def __init__(self, app: ASGIApp, config: TracingConfig) -> None:
        super().__init__(app, scopes={ScopeType.HTTP})  # The WebSocket is not supported
        self.open_telemetry_middleware = build_open_telemetry_middleware(app, config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.open_telemetry_middleware(scope, receive, send)  # type: ignore[arg-type]


def _get_wrapped_send(send: Send, request_span: dict[str, float]) -> Callable:
    @wraps(send)
    async def wrapped_send(message: Message) -> None:
        if message["type"] == "http.response.start":
            request_span["status_code"] = message["status"]

        if message["type"] == "http.response.body":
            request_span["duration"] = time.perf_counter() - request_span["start_time"]
        await send(message)

    return wrapped_send


class MetricsMiddleware(AbstractMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        metrics: MetricsManager,
        *,
        include_trace_exemplar: bool,
    ) -> None:
        super().__init__(app, scopes={ScopeType.HTTP})
        self.metrics = metrics
        self.include_exemplar = include_trace_exemplar

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request[Any, Any, Any](scope, receive)

        method = request.method
        path = scope["path_template"] if scope.get("path_template") else request.url.path

        self.metrics.inc_requests_count(method=method, path=path)
        self.metrics.add_request_in_progress(method=method, path=path)

        request_span = {
            "start_time": time.perf_counter(),
            "duration": 0,
            "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
        }

        wrapped_send = _get_wrapped_send(send, request_span)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            if request_span["status_code"] >= HTTP_500_INTERNAL_SERVER_ERROR:
                self.metrics.inc_requests_exceptions_count(
                    method=method,
                    path=path,
                    exception_type="UNSET",
                )

            exemplar: dict[str, str] | None = None

            if self.include_exemplar:
                span = trace.get_current_span()
                trace_id = trace.format_trace_id(span.get_span_context().trace_id)
                exemplar = {"TraceID": trace_id}

            self.metrics.observe_request_duration(
                method=method,
                path=path,
                duration=request_span["duration"],
                exemplar=exemplar,
            )

            self.metrics.inc_responses_count(
                method=method,
                path=path,
                status_code=request_span["status_code"],  # type: ignore[arg-type]
            )
            self.metrics.remove_request_in_progress(method=method, path=path)


@get(path="/metrics", summary="Get Prometheus metrics", include_in_schema=True)
async def get_metrics(request: Request) -> Response:
    registry = request.app.state.metrics_registry
    openmetrics_format = request.app.state.openmetrics_format
    response = get_latest_metrics(registry, openmetrics_format=openmetrics_format)
    return Response(
        content=response.payload,
        status_code=response.status_code,
        headers=response.headers,
    )


def build_tracing_middleware(config: TracingConfig) -> DefineMiddleware:
    """
    Build TracingMiddleware for a Litestar application.
    The function adds a TracingMiddleware to the Litestar application based on TracingConfig.

    :param TracingConfig config: The OpenTelemetry config.
    :returns: None
    """

    return DefineMiddleware(
        TracingMiddleware,
        config=config,
    )


def build_metrics_middleware(config: MetricsConfig) -> DefineMiddleware:
    """
    Build MetricsMiddleware for a Litestar application.

    :param MetricsConfig config: Configuration for the metrics.
    :returns: DefineMiddleware
    """

    metrics = build_metrics_manager(config)
    metrics.add_app_info()

    return DefineMiddleware(
        MetricsMiddleware,
        metrics=metrics,
        include_trace_exemplar=config.include_trace_exemplar,
    )


def add_metrics_endpoint(app: Litestar, registry: CollectorRegistry, *, openmetrics_format: bool = False) -> None:
    """
    Add CollectorRegistry in state and register /metrics endpoint.

    :param Litestar app: The Litestar application instance.
    :param CollectorRegistry registry: The registry for the metrics.
    :param bool openmetrics_format: A flag indicating whether to generate metrics in OpenMetrics format.
    :returns: None
    """

    app.state.metrics_registry = registry
    app.state.openmetrics_format = openmetrics_format
    app.register(get_metrics)
