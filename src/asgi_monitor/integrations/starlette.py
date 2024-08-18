from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.types import ASGIApp, Receive, Scope, Send

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.metrics.manager import MetricsManager, build_metrics_manager
from asgi_monitor.tracing.config import BaseTracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware

__all__ = (
    "TracingConfig",
    "TracingMiddleware",
    "setup_tracing",
    "MetricsConfig",
    "MetricsMiddleware",
    "setup_metrics",
)


def _get_route_details(scope: Scope) -> str | None:
    app = scope["app"]
    route = None

    for starlette_route in app.routes:
        match, _ = starlette_route.matches(scope)
        if match == Match.FULL:
            route = starlette_route.path
            break
        if match == Match.PARTIAL:
            route = starlette_route.path
    return route


def _get_default_span_details(scope: Scope) -> tuple[str, dict[str, Any]]:
    route = _get_route_details(scope)
    method = scope.get("method", "")
    attributes = {}
    if route:
        attributes[SpanAttributes.HTTP_ROUTE] = route
    if method and route:  # http
        span_name = f"{method} {route}"
    else:  # fallback
        span_name = method
    return span_name, attributes


def _get_path(request: Request) -> tuple[str, bool]:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path, True
    return request.url.path, False


@dataclass(slots=True, frozen=True)
class TracingConfig(BaseTracingConfig):
    """
    Configuration class for the OpenTelemetry middleware.
    Consult the OpenTelemetry ASGI documentation for more info about the configuration options.
    https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html
    """

    exclude_urls_env_key: str = "STARLETTE"
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

    metrics_prefix: str = "starlette"
    """The prefix to use for the metrics."""

    include_metrics_endpoint: bool = field(default=True)
    """Whether to include a /metrics endpoint."""

    openmetrics_format: bool = field(default=False)
    """A flag indicating whether to generate metrics in OpenMetrics format."""


class TracingMiddleware:
    __slots__ = ("app", "open_telemetry_middleware")

    def __init__(self, app: ASGIApp, config: TracingConfig) -> None:
        self.app = app
        self.open_telemetry_middleware = build_open_telemetry_middleware(app, config)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        return await self.open_telemetry_middleware(scope, receive, send)  # type: ignore[arg-type]


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        metrics: MetricsManager,
        *,
        include_trace_exemplar: bool,
    ) -> None:
        super().__init__(app)
        self.metrics = metrics
        self.include_exemplar = include_trace_exemplar

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.scope["type"] != "http":
            return await call_next(request)

        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        method = request.method
        path, is_handled_path = _get_path(request)

        if not is_handled_path:
            return await call_next(request)

        before_time = time.perf_counter()
        self.metrics.inc_requests_count(method=method, path=path)
        self.metrics.add_request_in_progress(method=method, path=path)

        try:
            response = await call_next(request)
        except Exception as exc:
            self.metrics.inc_requests_exceptions_count(
                method=method,
                path=path,
                exception_type=type(exc).__name__,
            )
            raise
        else:
            after_time = time.perf_counter()
            status_code = response.status_code
            exemplar: dict[str, str] | None = None

            if self.include_exemplar:
                span = trace.get_current_span()
                trace_id = trace.format_trace_id(span.get_span_context().trace_id)
                exemplar = {"TraceID": trace_id}

            self.metrics.observe_request_duration(
                method=method,
                path=path,
                duration=after_time - before_time,
                exemplar=exemplar,
            )
        finally:
            self.metrics.inc_responses_count(method=method, path=path, status_code=status_code)
            self.metrics.remove_request_in_progress(method=method, path=path)

        return response


async def get_metrics(request: Request) -> Response:
    registry = request.app.state.metrics_registry
    openmetrics_format = request.app.state.openmetrics_format
    response = get_latest_metrics(registry, openmetrics_format=openmetrics_format)
    return Response(
        content=response.payload,
        status_code=response.status_code,
        headers=response.headers,
    )


def setup_tracing(app: Starlette, config: TracingConfig) -> None:
    """
    Set up tracing for a Starlette application.
    The function adds a TracingMiddleware to the Starlette application based on TracingConfig.

    :param Starlette app: The FastAPI application instance.
    :param TracingConfig config: The OpenTelemetry config.
    :returns: None
    """

    app.add_middleware(TracingMiddleware, config=config)


def setup_metrics(app: Starlette, config: MetricsConfig) -> None:
    """
    Set up metrics for a Starlette application.
    This function adds a MetricsMiddleware to the Starlette application with the specified parameters.

    :param Starlette app: The Starlette application instance.
    :param MetricsConfig config: Configuration for the metrics.
    :returns: None
    """

    metrics = build_metrics_manager(config)
    metrics.add_app_info()

    app.add_middleware(
        MetricsMiddleware,
        metrics=metrics,
        include_trace_exemplar=config.include_trace_exemplar,
    )
    if config.include_metrics_endpoint:
        app.state.metrics_registry = config.registry
        app.state.openmetrics_format = config.openmetrics_format
        app.add_route(
            path="/metrics",
            route=get_metrics,
            methods=["GET"],
            name="Get Prometheus metrics",
            include_in_schema=True,
        )
