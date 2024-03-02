from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from opentelemetry.semconv.trace import SpanAttributes
from starlette.routing import Match

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.types import ASGIApp, Receive, Scope, Send

from asgi_monitor.tracing.config import _TracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware

__all__ = ("TracingConfig", "TracingMiddleware", "setup_monitoring")


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


def setup_monitoring(app: Starlette, config: TracingConfig) -> None:
    app.add_middleware(TracingMiddleware, config=config)
