from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from fastapi import FastAPI

from asgi_monitor.integrations.starlette import (
    MetricsMiddleware,
    TracingMiddleware,
    _get_default_span_details,
    get_metrics,
)

__all__ = (
    "TracingConfig",
    "TracingMiddleware",
    "MetricsMiddleware",
    "setup_tracing",
    "setup_metrics",
)


from asgi_monitor.tracing import _TracingConfig


@dataclass
class TracingConfig(_TracingConfig):
    exclude_urls_env_key: str = "FASTAPI"
    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]] = _get_default_span_details


def setup_tracing(app: FastAPI, config: TracingConfig) -> None:
    app.add_middleware(TracingMiddleware, config=config)


def setup_metrics(
    app: FastAPI,
    app_name: str,
    metrics_prefix: str = "fastapi",
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
