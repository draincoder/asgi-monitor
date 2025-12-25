import asyncio
import re
from typing import TYPE_CHECKING, cast

import pytest
from assertpy import assert_that
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import Span

from asgi_monitor.integrations.starlette import MetricsConfig, setup_metrics, setup_tracing
from asgi_monitor.metrics import get_latest_metrics
from tests.integration.factory import build_starlette_tracing_config, starlette_app


async def index(request: Request) -> JSONResponse:
    await asyncio.sleep(0.1)
    return JSONResponse({"hello": "world"})


async def error(request: Request) -> JSONResponse:
    result = 1 / 0
    return JSONResponse({"result": result})


async def one_parametrize(request: Request) -> JSONResponse:
    return JSONResponse({"result": request.path_params["param"]})


async def two_parametrize(request: Request) -> JSONResponse:
    return JSONResponse({"result": [request.path_params["param_a"], request.path_params["param_b"]]})


async def test_tracing() -> None:
    # Arrange
    trace_config, exporter = build_starlette_tracing_config()
    app = Starlette(routes=[Route("/", endpoint=index, methods=["GET"])])
    setup_tracing(app=app, config=trace_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get("/")

        # Assert
        first_span, second_span, third_span = cast("tuple[Span, Span, Span]", exporter.get_finished_spans())

        assert response.status_code == 200
        assert_that(first_span.attributes).is_equal_to(
            {"http.status_code": 200, "asgi.event.type": "http.response.start"},
        )
        assert_that(second_span.attributes).is_equal_to({"asgi.event.type": "http.response.body"})
        assert_that(third_span.attributes).is_equal_to(
            {
                "http.scheme": "http",
                "http.host": "testserver",
                "net.host.port": 80,
                "http.flavor": "1.1",
                "http.target": "/",
                "net.peer.ip": "testclient",
                "net.peer.port": 50000,
                "http.url": "http://testserver/",
                "http.method": "GET",
                "http.server_name": "testserver",
                "http.user_agent": "testclient",
                "http.route": "/",
                "http.status_code": 200,
            },
        )


async def test_tracing_with_empty_routes() -> None:
    # Arrange
    trace_config, exporter = build_starlette_tracing_config()
    app = Starlette(routes=[Route("/", endpoint=index, methods=["POST"])])
    setup_tracing(app=app, config=trace_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get("/")

        # Assert
        first_span, second_span, third_span = cast("tuple[Span, Span, Span]", exporter.get_finished_spans())
        assert response.status_code == 405
        assert_that(first_span.attributes).is_equal_to(
            {"http.status_code": 405, "asgi.event.type": "http.response.start"},
        )
        assert_that(second_span.attributes).is_equal_to({"asgi.event.type": "http.response.body"})
        assert_that(third_span.attributes).is_equal_to(
            {
                "http.scheme": "http",
                "http.host": "testserver",
                "net.host.port": 80,
                "http.flavor": "1.1",
                "http.target": "/",
                "http.url": "http://testserver/",
                "http.method": "GET",
                "http.server_name": "testserver",
                "http.user_agent": "testclient",
                "http.status_code": 405,
                "http.route": "/",
                "net.peer.ip": "testclient",
                "net.peer.port": 50000,
            },
        )


async def test_tracing_partial_match() -> None:
    # Arrange
    trace_config, exporter = build_starlette_tracing_config()
    app = Starlette()
    setup_tracing(app=app, config=trace_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get("/")

        # Assert
        first_span, second_span, third_span = cast("tuple[Span, Span, Span]", exporter.get_finished_spans())
        assert response.status_code == 404
        assert_that(first_span.attributes).is_equal_to(
            {"http.status_code": 404, "asgi.event.type": "http.response.start"},
        )
        assert_that(second_span.attributes).is_equal_to({"asgi.event.type": "http.response.body"})
        assert_that(third_span.attributes).is_equal_to(
            {
                "http.scheme": "http",
                "http.host": "testserver",
                "net.host.port": 80,
                "http.flavor": "1.1",
                "http.target": "/",
                "http.url": "http://testserver/",
                "http.method": "GET",
                "http.server_name": "testserver",
                "http.user_agent": "testclient",
                "http.status_code": 404,
                "net.peer.ip": "testclient",
                "net.peer.port": 50000,
            },
        )


async def test_metrics() -> None:
    # Arrange
    expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
    app = Starlette()
    metrics_config = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        openmetrics_format=False,
    )
    setup_metrics(app=app, config=metrics_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == expected_content_type
        assert_that(response.content.decode()).contains(
            'starlette_app_info{app_name="test"} 1.0',
            'starlette_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
            'starlette_requests_created{app_name="test",method="GET",path="/metrics"}',
            'starlette_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
        )


async def test_error_metrics() -> None:
    # Arrange
    app = Starlette(routes=[Route("/error", endpoint=error, methods=["GET"])])
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=True, include_trace_exemplar=False)
    setup_metrics(app=app, config=metrics_config)

    # Act
    async with starlette_app(app) as client:
        try:
            client.get("/error")
        except ZeroDivisionError:
            # Assert
            response = client.get("/metrics")
            assert response.status_code == 200
            assert_that(response.content.decode()).contains(
                'starlette_requests_total{app_name="test",method="GET",path="/error"} 1.0',
                'starlette_requests_created{app_name="test",method="GET",path="/error"}',
                'starlette_requests_in_progress{app_name="test",method="GET",path="/error"} 0.0',
                "starlette_requests_exceptions_total{"
                'app_name="test",exception_type="ZeroDivisionError",method="GET",path="/error"} 1.0',
                "starlette_requests_exceptions_created{"
                'app_name="test",exception_type="ZeroDivisionError",method="GET",path="/error"}',
                'starlette_responses_total{app_name="test",method="GET",path="/error",status_code="500"} 1.0',
                'starlette_responses_created{app_name="test",method="GET",path="/error",status_code="500"}',
            )


@pytest.mark.parametrize(
    ("request_path", "expected_template"),
    [
        ("/", "/"),
        ("/params/one", "/params/{param}"),
        ("/params/one/two", "/params/{param_a}/{param_b}"),
    ],
)
async def test_metrics_with_tracing(request_path: str, expected_template: str) -> None:
    # Arrange
    trace_config, exporter = build_starlette_tracing_config()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=False, include_trace_exemplar=True)
    app = Starlette(
        routes=[
            Route("/", endpoint=index, methods=["GET"]),
            Route("/params/{param}", endpoint=one_parametrize, methods=["GET"]),
            Route("/params/{param_a}/{param_b}", endpoint=two_parametrize, methods=["GET"]),
        ]
    )

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get(request_path)

        # Assert
        assert response.status_code == 200
        assert all(f"GET {expected_template}" in s.name for s in exporter.get_finished_spans())

        metrics = get_latest_metrics(metrics_config.registry, openmetrics_format=True)
        escaped_template = re.escape(expected_template)
        pattern = (
            r"starlette_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="'
            + escaped_template
            + r'"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
        )
        assert_that(metrics.payload.decode()).matches(pattern)


async def test_metrics_openmetrics_with_tracing() -> None:
    # Arrange
    expected_content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
    trace_config, _ = build_starlette_tracing_config()
    metrics_config = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=True,
        openmetrics_format=True,
    )
    app = Starlette(routes=[Route("/", endpoint=index, methods=["GET"])])

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    # Act
    async with starlette_app(app) as client:
        response = client.get("/")
        metrics = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert metrics.status_code == 200
        assert metrics.headers["content-type"] == expected_content_type
        pattern = (
            r"starlette_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
        )
        assert_that(metrics.content.decode()).matches(pattern)
