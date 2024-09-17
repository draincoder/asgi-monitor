import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine

from aiohttp.web import Application, Request, Response, middleware
from aiohttp.web_exceptions import HTTPInternalServerError
from opentelemetry import trace

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.metrics.manager import MetricsManager, build_metrics_manager

__all__ = ("MetricsConfig", "build_metrics_middleware", "get_metrics", "setup_metrics")


@dataclass(slots=True, frozen=True)
class MetricsConfig(BaseMetricsConfig):
    """Configuration class for the Metrics middleware."""

    metrics_prefix: str = "starlette"
    """The prefix to use for the metrics."""

    include_metrics_endpoint: bool = field(default=True)
    """Whether to include a /metrics endpoint."""

    openmetrics_format: bool = field(default=False)
    """A flag indicating whether to generate metrics in OpenMetrics format."""


def build_metrics_middleware(
    metrics: MetricsManager,
    *,
    include_trace_exemplar: bool,
) -> Coroutine:
    @middleware
    async def metrics_middleware(request: Request, handler: Callable) -> Response:
        status_code = HTTPInternalServerError
        method = request.method
        path = request.url.path

        before_time = time.perf_counter()
        metrics.inc_requests_count(method=method, path=path)
        metrics.add_request_in_progress(method=method, path=path)

        try:
            response = await handler(request)
        except Exception as exc:
            metrics.inc_requests_exceptions_count(
                method=method,
                path=path,
                exception_type=type(exc).__name__,
            )
            raise
        else:
            after_time = time.perf_counter()
            status_code = response._status
            exemplar: dict[str, str] | None = None

            if include_trace_exemplar:
                span = trace.get_current_span()
                trace_id = trace.format_trace_id(span.get_span_context().trace_id)
                exemplar = {"TraceID": trace_id}

            metrics.observe_request_duration(
                method=method,
                path=path,
                duration=after_time - before_time,
                exemplar=exemplar,
            )
        finally:
            metrics.inc_responses_count(method=method, path=path, status_code=status_code)
            metrics.remove_request_in_progress(method=method, path=path)

        return response

    return metrics_middleware


async def get_metrics(request: Request) -> Response:
    registry = request.app.metrics_registry
    openmetrics_format = request.app.openmetrics_format
    response = get_latest_metrics(registry, openmetrics_format=openmetrics_format)
    return Response(
        body=response.payload,
        status=response.status_code,
        headers=response.headers,
    )


def setup_metrics(app: Application, config: MetricsConfig) -> None:
    metrics = build_metrics_manager(config)
    metrics.add_app_info()

    metrics_middleware = build_metrics_middleware(metrics=metrics, include_trace_exemplar=config.include_trace_exemplar)
    app._middlewares.append(metrics_middleware)

    if config.include_metrics_endpoint:
        app.metrics_registry = config.registry
        app.openmetrics_format = config.openmetrics_format
        app.router.add_get(path="/metrics", handler=get_metrics, name="Get_Prometheus_metrics")
