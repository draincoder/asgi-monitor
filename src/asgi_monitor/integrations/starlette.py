from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.container import MetricsContainer
from asgi_monitor.metrics.manager import MetricsManager

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.types import ASGIApp, Receive, Scope, Send

from asgi_monitor.tracing.config import _TracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware

__all__ = (
    "TracingConfig",
    "TracingMiddleware",
    "MetricsMiddleware",
    "setup_tracing",
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
    elif route:  # websocket
        span_name = route
    else:  # fallback
        span_name = method
    return span_name, attributes


def _get_path(request: Request) -> tuple[str, bool]:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path, True
    return request.url.path, False


@dataclass
class TracingConfig(_TracingConfig):
    exclude_urls_env_key: str = "STARLETTE"
    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]] = _get_default_span_details


class TracingMiddleware:
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
            return await self.app(scope, receive, send)  # type: ignore[no-any-return]

        return await self.open_telemetry_middleware(scope, receive, send)  # type: ignore[no-any-return]


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        app_name: str,
        metrics_prefix: str,
        include_trace: bool,
    ) -> None:
        super().__init__(app)
        container = MetricsContainer(prefix=metrics_prefix)
        self.metrics = MetricsManager(app_name=app_name, container=container)
        self.include_trace = include_trace
        self.metrics.add_app_info()

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

            if self.include_trace:
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
    response = get_latest_metrics(openmetrics_format=False)
    return Response(
        content=response.payload,
        status_code=response.status_code,
        headers=response.headers,
    )


def setup_tracing(app: Starlette, config: TracingConfig) -> None:
    app.add_middleware(TracingMiddleware, config=config)


def setup_metrics(
    app: Starlette,
    app_name: str,
    metrics_prefix: str = "starlette",
    include_trace: bool = False,
    include_metrics_endpoint: bool = True,
) -> None:
    app.add_middleware(
        MetricsMiddleware,
        app_name=app_name,
        metrics_prefix=metrics_prefix,
        include_trace=include_trace,
    )
    if include_metrics_endpoint:
        app.add_route(
            path="/metrics/",
            route=get_metrics,
            methods=["GET"],
            name="Get Prometheus metrics",
            include_in_schema=True,
        )
