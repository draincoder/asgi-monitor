import time
from dataclasses import dataclass, field
from timeit import default_timer
from typing import Any, Callable, Coroutine

from aiohttp.web import Application, Request, Response, middleware
from aiohttp.web_exceptions import HTTPException, HTTPInternalServerError
from multidict import CIMultiDictProxy  # noqa: TCH002
from opentelemetry import trace
from opentelemetry.instrumentation.asgi import collect_request_attributes
from opentelemetry.instrumentation.utils import http_status_to_status_code
from opentelemetry.metrics import Meter, MeterProvider, get_meter_provider
from opentelemetry.propagate import extract
from opentelemetry.propagators.textmap import Getter
from opentelemetry.semconv.metrics import MetricInstruments
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode, Tracer, TracerProvider

from asgi_monitor.metrics import get_latest_metrics
from asgi_monitor.metrics.config import BaseMetricsConfig
from asgi_monitor.metrics.manager import MetricsManager, build_metrics_manager

__all__ = ("MetricsConfig", "build_metrics_middleware", "get_metrics", "setup_metrics")

from asgi_monitor.tracing import BaseTracingConfig

OTEL_SCHEMA = "https://opentelemetry.io/schemas/1.11.0"

_duration_attrs = [
    SpanAttributes.HTTP_METHOD,
    SpanAttributes.HTTP_HOST,
    SpanAttributes.HTTP_SCHEME,
    SpanAttributes.HTTP_STATUS_CODE,
    SpanAttributes.HTTP_FLAVOR,
    SpanAttributes.HTTP_SERVER_NAME,
    SpanAttributes.NET_HOST_NAME,
    SpanAttributes.NET_HOST_PORT,
    SpanAttributes.HTTP_ROUTE,
]

_active_requests_count_attrs = [
    SpanAttributes.HTTP_METHOD,
    SpanAttributes.HTTP_HOST,
    SpanAttributes.HTTP_SCHEME,
    SpanAttributes.HTTP_FLAVOR,
    SpanAttributes.HTTP_SERVER_NAME,
]


class AiohttpGetter(Getter):
    def get(self, carrier: dict, key: str) -> list | None:
        headers: CIMultiDictProxy = carrier.headers  # type: ignore[attr-defined]
        if not headers:
            return None
        return headers.getall(key, None)

    def keys(self, carrier: dict) -> list:
        return list(carrier.keys())


getter = AiohttpGetter()


def _get_tracer(tracer_provider: TracerProvider | None = None) -> Tracer:
    return trace.get_tracer(
        __name__,
        tracer_provider=tracer_provider,
        schema_url=OTEL_SCHEMA,
    )


def get_meter(
    name: str,
    version: str = "",
    meter_provider: MeterProvider | None = None,
    schema_url: str | None = None,
) -> Meter:
    if meter_provider is None:
        meter_provider = get_meter_provider()
    return meter_provider.get_meter(name, version, schema_url)


def _parse_duration_attrs(req_attrs: dict[str, Any]) -> dict[str, Any]:
    duration_attrs = {}
    for attr_key in _duration_attrs:
        if req_attrs.get(attr_key) is not None:
            duration_attrs[attr_key] = req_attrs[attr_key]
    return duration_attrs


def _parse_active_request_count_attrs(req_attrs: dict[str, Any]) -> dict[str, Any]:
    active_requests_count_attrs = {}
    for attr_key in _active_requests_count_attrs:
        if req_attrs.get(attr_key) is not None:
            active_requests_count_attrs[attr_key] = req_attrs[attr_key]
    return active_requests_count_attrs


def get_default_span_details(request: Request) -> tuple[str, dict]:
    span_name = request.path.strip() or f"HTTP {request.method}"
    return span_name, {}


def set_status_code(span: trace.Span, status_code: int) -> None:
    try:
        status_code = int(status_code)
    except ValueError:
        span.set_status(
            Status(
                StatusCode.ERROR,
                "Non-integer HTTP status: " + repr(status_code),
            )
        )
    else:
        span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status_code)
        span.set_status(Status(http_status_to_status_code(status_code, server_span=True)))


@dataclass(slots=True, frozen=True)
class MetricsConfig(BaseMetricsConfig):
    """Configuration class for the Metrics middleware."""

    metrics_prefix: str = "starlette"
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

    exclude_urls_env_key: str = "AIOHTTP"
    """
    Key to use when checking whether a list of excluded urls is passed via ENV.
    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'.
    """


def build_metrics_middleware(
    metrics_manager: MetricsManager,
    *,
    include_trace_exemplar: bool,
) -> Callable[..., Coroutine]:
    @middleware
    async def metrics_middleware(request: Request, handler: Callable) -> Any:
        status_code = HTTPInternalServerError
        method = request.method
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
            status_code = response._status  # noqa: SLF001
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
            metrics_manager.inc_responses_count(method=method, path=path, status_code=status_code)  # type: ignore[arg-type]
            metrics_manager.remove_request_in_progress(method=method, path=path)

        return response

    return metrics_middleware


def build_tracing_middleware(app: Application, config: TracingConfig) -> Callable[..., Coroutine]:
    tracer = _get_tracer(config.tracer_provider)
    meter = get_meter(
        name="AIOHTTP",
        meter_provider=config.meter_provider,
        schema_url=OTEL_SCHEMA,
    )
    duration_histogram = meter.create_histogram(
        name=MetricInstruments.HTTP_SERVER_DURATION,
        unit="ms",
        description="Measures the duration of inbound HTTP requests.",
    )

    active_requests_counter = meter.create_up_down_counter(
        name=MetricInstruments.HTTP_SERVER_ACTIVE_REQUESTS,
        unit="requests",
        description="measures the number of concurrent HTTP requests those are currently in flight",
    )

    @middleware
    async def tracing_middleware(request: Request, handler: Callable) -> Any:
        span_name, additional_attributes = get_default_span_details(request)

        req_attrs = collect_request_attributes(request)
        duration_attrs = _parse_duration_attrs(req_attrs)
        active_requests_count_attrs = _parse_active_request_count_attrs(req_attrs)

        with tracer.start_as_current_span(
            span_name,
            context=extract(request, getter=getter),
            kind=trace.SpanKind.SERVER,
        ) as span:
            attributes = collect_request_attributes(request)
            attributes.update(additional_attributes)
            span.set_attributes(attributes)
            start = default_timer()
            active_requests_counter.add(1, active_requests_count_attrs)
            try:
                resp = await handler(request)
                set_status_code(span, resp.status)
            except HTTPException as ex:
                set_status_code(span, ex.status_code)
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
    metrics = build_metrics_manager(config)
    metrics.add_app_info()

    metrics_middleware = build_metrics_middleware(
        metrics_manager=metrics, include_trace_exemplar=config.include_trace_exemplar
    )
    app._middlewares.append(metrics_middleware)  # noqa: SLF001

    if config.include_metrics_endpoint:
        app.metrics_registry = config.registry
        app.openmetrics_format = config.openmetrics_format
        app.router.add_get(path="/metrics", handler=get_metrics, name="Get_Prometheus_metrics")


def setup_tracing(app: Application, config: TracingConfig) -> None:
    app._middlewares.append(build_tracing_middleware(app, config))  # noqa: SLF001
