import asyncio
from typing import TYPE_CHECKING, cast

from assertpy import assert_that
from litestar import Litestar, get

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import Span

from asgi_monitor.integrations.litestar import (
    MetricsConfig,
    add_metrics_endpoint,
    build_metrics_middleware,
    build_tracing_middleware,
)
from asgi_monitor.metrics import get_latest_metrics
from tests.integration.factory import build_litestar_tracing_config, litestar_app


@get("/")
async def index() -> dict[str, str]:
    await asyncio.sleep(0.1)
    return {"hello": "world"}


@get("/error")
async def error() -> dict[str, float]:
    result = 1 / 0
    return {"result": result}


async def test_tracing() -> None:
    # Arrange
    trace_config, exporter = build_litestar_tracing_config()
    app = Litestar([index], middleware=[build_tracing_middleware(trace_config)])

    # Act
    async with litestar_app(app) as client:
        response = client.get("/")

        # Assert
        first_span, second_span, third_span = cast("tuple[Span, Span, Span]", exporter.get_finished_spans())

        assert response.status_code == 200
        assert_that(first_span.attributes).is_equal_to({"http.status_code": 200, "type": "http.response.start"})
        assert_that(second_span.attributes).is_equal_to({"type": "http.response.body"})
        assert_that(third_span.attributes).is_equal_to(
            {
                "http.scheme": "http",
                "http.host": "testserver.local",
                "net.host.port": 80,
                "http.flavor": "1.1",
                "http.target": "/",
                "http.url": "http://testserver.local/",
                "http.method": "GET",
                "http.server_name": "testserver.local",
                "http.user_agent": "testclient",
                "http.route": "/",
                "http.status_code": 200,
                "net.peer.ip": "testclient",
                "net.peer.port": 50000,
            },
        )


async def test_metrics() -> None:
    # Arrange
    metrics_config = MetricsConfig(app_name="test", include_trace_exemplar=False)
    app = Litestar(middleware=[build_metrics_middleware(metrics_config)])
    add_metrics_endpoint(app, metrics_config.registry)

    # Act
    async with litestar_app(app) as client:
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert_that(response.content.decode()).contains(
            'litestar_app_info{app_name="test"} 1.0',
            'litestar_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
            'litestar_requests_created{app_name="test",method="GET",path="/metrics"}',
            'litestar_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
        )


async def test_error_metrics() -> None:
    # Arrange
    metrics_config = MetricsConfig(app_name="test", include_trace_exemplar=True)
    app = Litestar([error], middleware=[build_metrics_middleware(metrics_config)])
    add_metrics_endpoint(app, metrics_config.registry)

    # Act
    async with litestar_app(app) as client:
        client.get("/error")
        # Assert
        response = client.get("/metrics")
        assert response.status_code == 200
        assert_that(response.content.decode()).contains(
            'litestar_requests_total{app_name="test",method="GET",path="/error"} 1.0',
            'litestar_requests_created{app_name="test",method="GET",path="/error"}',
            'litestar_requests_in_progress{app_name="test",method="GET",path="/error"} 0.0',
            "litestar_requests_exceptions_total{"
            'app_name="test",exception_type="UNSET",method="GET",path="/error"} 1.0',
            "litestar_requests_exceptions_created{"
            'app_name="test",exception_type="UNSET",method="GET",path="/error"}',
            'litestar_responses_total{app_name="test",method="GET",path="/error",status_code="500"} 1.0',
            'litestar_responses_created{app_name="test",method="GET",path="/error",status_code="500"}',
        )


async def test_metrics_with_tracing() -> None:
    # Arrange
    trace_config, _ = build_litestar_tracing_config()
    metrics_config = MetricsConfig(app_name="test", include_trace_exemplar=True)
    middlewares = [build_tracing_middleware(trace_config), build_metrics_middleware(metrics_config)]
    app = Litestar([index], middleware=middlewares)

    # Act
    async with litestar_app(app) as client:
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        metrics = get_latest_metrics(metrics_config.registry, openmetrics_format=True)
        pattern = (
            r"litestar_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
        )
        assert_that(metrics.payload.decode()).matches(pattern)
