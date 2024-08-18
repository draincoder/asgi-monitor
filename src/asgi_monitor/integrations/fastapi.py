from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from asgi_monitor.metrics.manager import build_metrics_manager

if TYPE_CHECKING:
    from fastapi import FastAPI

from asgi_monitor.integrations.starlette import (
    MetricsMiddleware,
    TracingMiddleware,
    _get_default_span_details,
    get_metrics,
)
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.tracing import BaseTracingConfig

__all__ = (
    "TracingConfig",
    "TracingMiddleware",
    "setup_tracing",
    "MetricsConfig",
    "MetricsMiddleware",
    "setup_metrics",
)


@dataclass(slots=True, frozen=True)
class MetricsConfig(BaseMetricsConfig):
    """Configuration class for the Metrics middleware."""

    metrics_prefix: str = "fastapi"
    """The prefix to use for the metrics."""

    include_metrics_endpoint: bool = field(default=True)
    """Whether to include a /metrics endpoint."""

    openmetrics_format: bool = field(default=False)
    """A flag indicating whether to generate metrics in OpenMetrics format."""


@dataclass(slots=True, frozen=True)
class TracingConfig(BaseTracingConfig):
    """
    Configuration class for the OpenTelemetry middleware.
    Consult the OpenTelemetry ASGI documentation for more info about the configuration options.
    https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html
    """

    exclude_urls_env_key: str = "FASTAPI"
    """
    Key to use when checking whether a list of excluded urls is passed via ENV.
    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'.
    """

    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]] = _get_default_span_details
    """
    Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """


def setup_tracing(app: FastAPI, config: TracingConfig) -> None:
    """
    Set up tracing for a FastAPI application.
    The function adds a TracingMiddleware to the FastAPI application based on TracingConfig.

    :param FastAPI app: The FastAPI application instance.
    :param TracingConfig config: The OpenTelemetry config.
    :returns: None
    """

    app.add_middleware(TracingMiddleware, config=config)


def setup_metrics(app: FastAPI, config: MetricsConfig) -> None:
    """
    Set up metrics for a FastAPI application.
    This function adds a MetricsMiddleware to the FastAPI application with the specified parameters.

    :param FastAPI app: The FastAPI application instance.
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
