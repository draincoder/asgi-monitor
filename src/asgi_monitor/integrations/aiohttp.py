import time
from dataclasses import dataclass, field
from timeit import default_timer
from typing import Any, Callable, Coroutine

from aiohttp.web import Application, Request, Response, middleware
from aiohttp.web_exceptions import HTTPException, HTTPInternalServerError
from aiohttp.web_urldispatcher import MatchInfoError
from opentelemetry import trace
from opentelemetry.instrumentation.utils import http_status_to_status_code
from opentelemetry.metrics import Meter, MeterProvider, get_meter_provider
from opentelemetry.propagate import extract
from opentelemetry.propagators.textmap import Getter
from opentelemetry.semconv.metrics import MetricInstruments
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, Tracer, TracerProvider

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.metrics.manager import MetricsManager, build_metrics_manager

__all__ = (
    "MetricsConfig",
    "get_metrics",
    "setup_metrics",
    "TracingConfig",
    "setup_tracing",
)


_OTEL_SCHEMA = "https://opentelemetry.io/schemas/1.11.0"


class AiohttpGetter(Getter):
    def get(self, carrier: Request, key: str) -> list[str] | None:
        headers = carrier.headers
        return headers.getall(key, None) if headers else None

    def keys(self, carrier: Request) -> list[str]:
        return list(carrier.keys())


def _get_default_span_details(request: Request) -> tuple[str, dict[str, Any]]:
    span_attributes: dict[str, Any] = {
        SpanAttributes.HTTP_SCHEME: request.scheme,
        SpanAttributes.HTTP_HOST: request.host,
        SpanAttributes.NET_HOST_PORT: request.url.port,
        SpanAttributes.HTTP_FLAVOR: f"{request.version.major}.{request.version.minor}",
        SpanAttributes.HTTP_TARGET: request.path_qs,
        SpanAttributes.HTTP_URL: str(request.url),
        SpanAttributes.HTTP_METHOD: request.method,
        SpanAttributes.HTTP_SERVER_NAME: request.headers.get("Host", ""),
        SpanAttributes.HTTP_USER_AGENT: request.headers.get("User-Agent", ""),
        SpanAttributes.NET_PEER_IP: request.remote,
    }

    if request.transport:
        span_attributes[SpanAttributes.NET_PEER_PORT] = request.transport.get_extra_info("peername")[1]
    if request.match_info.route and request.match_info.route.resource:
        route = request.match_info.route.resource.canonical
        span_attributes[SpanAttributes.HTTP_ROUTE] = route
    else:
        route = request.path
        span_attributes[SpanAttributes.HTTP_ROUTE] = route

    return f"{request.method} {route or 'unknown'}", span_attributes


def _set_status_code(span: trace.Span, status_code: int) -> None:
    status_code = int(status_code)
    span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status_code)
    span.set_status(Status(http_status_to_status_code(status_code, server_span=True)))


@dataclass(slots=True, frozen=True)
class MetricsConfig(BaseMetricsConfig):
    """Configuration class for the Metrics middleware."""

    metrics_prefix: str = "aiohttp"
    """The prefix to use for the metrics."""

    include_metrics_endpoint: bool = field(default=True)
    """Whether to include a /metrics endpoint."""

    openmetrics_format: bool = field(default=False)
    """A flag indicating whether to generate metrics in OpenMetrics format."""


@dataclass(slots=True, frozen=True)
class TracingConfig:
    """Configuration class for the OpenTelemetry middleware."""

    scope_span_details_extractor: Callable[[Request], tuple[str, dict[str, Any]]] = _get_default_span_details
    """
    Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """

    meter_provider: MeterProvider | None = field(default=None)
    """Optional meter provider to use."""

    tracer_provider: TracerProvider | None = field(default=None)
    """Optional tracer provider to use."""


def build_metrics_middleware(
    metrics_manager: MetricsManager,
    *,
    include_trace_exemplar: bool,
) -> Callable[..., Coroutine]:
    @middleware
    async def metrics_middleware(request: Request, handler: Callable) -> Any:
        if isinstance(await request.app.router.resolve(request), MatchInfoError):
            return await handler(request)

        status_code = HTTPInternalServerError.status_code

        method = request.method
        if request.match_info.route and request.match_info.route.resource:
            path = request.match_info.route.resource.canonical
        else:
            path = request.url.path

        before_time = time.perf_counter()
        metrics_manager.inc_requests_count(method=method, path=path)
        metrics_manager.add_request_in_progress(method=method, path=path)

        try:
            response = await handler(request)
        except Exception as exc:
            metrics_manager.inc_requests_exceptions_count(
                method=method,
                path=path,
                exception_type=type(exc).__name__,
            )
            raise
        else:
            after_time = time.perf_counter()
            status_code = response.status

            exemplar: dict[str, str] | None = None

            if include_trace_exemplar:
                span = trace.get_current_span()
                trace_id = trace.format_trace_id(span.get_span_context().trace_id)
                exemplar = {"TraceID": trace_id}

            metrics_manager.observe_request_duration(
                method=method,
                path=path,
                duration=after_time - before_time,
                exemplar=exemplar,
            )
        finally:
            metrics_manager.inc_responses_count(method=method, path=path, status_code=status_code)
            metrics_manager.remove_request_in_progress(method=method, path=path)

        return response

    return metrics_middleware


def build_tracing_middleware(config: TracingConfig) -> Callable[..., Coroutine]:
    tracer = _get_tracer(config.tracer_provider)
    meter = _get_meter(
        name="aiohttp",
        meter_provider=config.meter_provider,
        schema_url=_OTEL_SCHEMA,
    )
    duration_histogram = meter.create_histogram(
        name=MetricInstruments.HTTP_SERVER_DURATION,
        unit="ms",
        description="Measures the duration of inbound HTTP requests.",
    )
    active_requests_counter = meter.create_up_down_counter(
        name=MetricInstruments.HTTP_SERVER_ACTIVE_REQUESTS,
        unit="requests",
        description="Measures the number of concurrent HTTP requests those are currently in flight",
    )
    getter = AiohttpGetter()

    @middleware
    async def tracing_middleware(request: Request, handler: Callable) -> Any:
        span_name, attributes = config.scope_span_details_extractor(request)
        active_requests_count_attrs = {
            SpanAttributes.HTTP_SERVER_NAME: attributes[SpanAttributes.HTTP_SERVER_NAME],
            SpanAttributes.HTTP_SCHEME: attributes[SpanAttributes.HTTP_SCHEME],
            SpanAttributes.HTTP_HOST: attributes[SpanAttributes.HTTP_HOST],
            SpanAttributes.HTTP_FLAVOR: attributes[SpanAttributes.HTTP_FLAVOR],
            SpanAttributes.HTTP_METHOD: attributes[SpanAttributes.HTTP_METHOD],
        }
        duration_attrs = {SpanAttributes.HTTP_ROUTE: attributes[SpanAttributes.HTTP_ROUTE]}

        with tracer.start_as_current_span(
            span_name,
            context=extract(request, getter=getter),
            kind=trace.SpanKind.SERVER,
        ) as span:
            request.span = span
            span.set_attributes(attributes)
            start = default_timer()
            active_requests_counter.add(1, active_requests_count_attrs)
            try:
                resp = await handler(request)
                _set_status_code(span, resp.status)
            except HTTPException as exc:
                _set_status_code(span, exc.status_code)
                raise
            finally:
                duration = max((default_timer() - start) * 1000, 0)
                duration_histogram.record(duration, duration_attrs)
                active_requests_counter.add(-1, active_requests_count_attrs)
            return resp

    return tracing_middleware


async def get_metrics(request: Request) -> Response:
    registry = request.app.metrics_registry  # type: ignore[attr-defined]
    openmetrics_format = request.app.openmetrics_format  # type: ignore[attr-defined]
    response = get_latest_metrics(registry, openmetrics_format=openmetrics_format)
    return Response(
        body=response.payload,
        status=response.status_code,
        headers=response.headers,
    )


def setup_metrics(app: Application, config: MetricsConfig) -> None:
    """
    Set up metrics for an Aiohttp application.
    This function adds a metrics_middleware to the Aiohttp application with the specified parameters.

    :param Aiohttp app: The Aiohttp application instance.
    :param MetricsConfig config: Configuration for the metrics.
    :returns: None
    """

    metrics = build_metrics_manager(config)
    metrics.add_app_info()

    metrics_middleware = build_metrics_middleware(
        metrics_manager=metrics, include_trace_exemplar=config.include_trace_exemplar
    )
    app.middlewares.append(metrics_middleware)

    if config.include_metrics_endpoint:
        app.metrics_registry = config.registry
        app.openmetrics_format = config.openmetrics_format
        app.router.add_get(path="/metrics", handler=get_metrics)


def setup_tracing(app: Application, config: TracingConfig) -> None:
    """
    Set up tracing for an Aiohttp application.
    The function adds a tracing_middleware to the Aiohttp application based on TracingConfig.

    :param Aiohttp app: The Aiohttp application instance.
    :param TracingConfig config: The OpenTelemetry config.
    :return: None
    """

    app.middlewares.append(build_tracing_middleware(config))


def _get_tracer(tracer_provider: TracerProvider | None = None) -> Tracer:
    return trace.get_tracer(
        __name__,
        tracer_provider=tracer_provider,
        schema_url=_OTEL_SCHEMA,
    )


def _get_meter(
    name: str,
    meter_provider: MeterProvider | None = None,
    schema_url: str | None = None,
) -> Meter:
    if meter_provider is None:
        meter_provider = get_meter_provider()
    return meter_provider.get_meter(name=name, schema_url=schema_url)
