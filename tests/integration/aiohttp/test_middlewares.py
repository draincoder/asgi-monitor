import asyncio
import json
from typing import Callable, cast

from aiohttp.test_utils import TestClient  # noqa: TCH002
from aiohttp.web import Application, Request, Response, json_response
from aiohttp.web_exceptions import HTTPInternalServerError
from assertpy import assert_that
from prometheus_client import REGISTRY

from asgi_monitor.integrations.aiohttp import MetricsConfig, setup_metrics, setup_tracing
from asgi_monitor.metrics import get_latest_metrics
from tests.integration.factory import build_aiohttp_tracing_config


async def index_handler(request: Request) -> Response:
    await asyncio.sleep(0.1)
    return Response(body=json.dumps({"hello": "world"}))


async def zero_division_handler(request: Request) -> Response:
    return Response(body=json.dumps({"value": 1 / 0}))


async def json_response_handler(request: Request) -> Response:
    return json_response({"hello": "world"})


async def raise_handler(request: Request) -> Response:
    raise HTTPInternalServerError()


async def test_metrics(aiohttp_client: Callable) -> None:
    # Arrange
    expected_content_type = "text/plain; version=0.0.4; charset=utf-8"

    app = Application()

    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        openmetrics_format=False,
    )

    setup_metrics(app, metrics_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/metrics")
    # Assert
    assert response.headers["content-type"] == expected_content_type
    assert response.status == 200
    assert_that(await response.text()).contains(
        'aiohttp_app_info{app_name="test"} 1.0',
        'aiohttp_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
        'aiohttp_requests_created{app_name="test",method="GET",path="/metrics"}',
        'aiohttp_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
    )


async def test_metrics_global_registry(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()

    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        registry=REGISTRY,
    )

    setup_metrics(app, metrics_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/metrics")
    # Assert
    assert response.status == 200
    assert_that(await response.text()).contains(
        'aiohttp_app_info{app_name="test"} 1.0',
        'aiohttp_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
        'aiohttp_requests_created{app_name="test",method="GET",path="/metrics"}',
        'aiohttp_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
    )


async def test_metrics_get_path(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()

    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
    )

    setup_metrics(app, metrics_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/metrics")
    # Assert
    assert response.status == 200
    assert_that(await response.text()).contains(
        'aiohttp_app_info{app_name="test"} 1.0',
        'aiohttp_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
        'aiohttp_requests_created{app_name="test",method="GET",path="/metrics"}',
        'aiohttp_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
    )


async def test_metrics_with_tracing(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()
    app.router.add_get("/", index_handler)

    trace_cfg, exporter = build_aiohttp_tracing_config()
    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=False,
        include_trace_exemplar=True,
    )

    setup_metrics(app, metrics_cfg)
    setup_tracing(app, trace_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/")
    # Assert
    assert response.status == 200
    metrics = get_latest_metrics(metrics_cfg.registry, openmetrics_format=True)
    span = exporter.get_finished_spans()[0]
    pattern = (
        r"aiohttp_request_duration_seconds_bucket\{"
        r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
    )
    assert_that(metrics.payload.decode()).matches(pattern)
    assert_that(metrics.payload.decode()).contains('aiohttp_app_info{app_name="test"} 1.0')


async def test_metrics_openmetrics_with_tracing(aiohttp_client: Callable) -> None:
    # Arrange
    expected_content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"

    app = Application()
    app.router.add_get("/", index_handler)

    trace_cfg, _ = build_aiohttp_tracing_config()
    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=True,
        openmetrics_format=True,
    )

    setup_metrics(app, metrics_cfg)
    setup_tracing(app, trace_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/")
    metrics = await client.get("/metrics")
    # Assert
    assert response.status == 200
    assert metrics.status == 200
    assert metrics.headers["content-type"] == expected_content_type
    pattern = (
        r"aiohttp_request_duration_seconds_bucket\{"
        r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
    )
    metrics_content = await metrics.text()
    assert_that(metrics_content).matches(pattern)
    assert_that(metrics_content).contains('aiohttp_app_info{app_name="test"} 1.0')


async def test_handle_exception(aiohttp_client: Callable) -> None:
    # Arrange
    expected_content_type = "text/plain; version=0.0.4; charset=utf-8"

    app = Application()
    app.router.add_get("/error", zero_division_handler)

    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        openmetrics_format=False,
    )

    setup_metrics(app, metrics_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    try:
        exc = await client.get("/error")
    except ZeroDivisionError:
        response = await client.get("/metrics")
        # Assert
        assert response.headers["content-type"] == expected_content_type
        assert response.status == 200
        assert exc.status == 5001
        metrics_content = await response.text()
        assert_that(metrics_content).contains(
            'aiohttp_requests_total{app_name="test",method="GET",path="/error"} 1.0',
            'aiohttp_requests_created{app_name="test",method="GET",path="/error"}',
            'aiohttp_requests_in_progress{app_name="test",method="GET",path="/error"} 0.0',
            "aiohttp_requests_exceptions_total{"
            'app_name="test",exception_type="ZeroDivisionError",method="GET",path="/error"} 1.0',
            "aiohttp_requests_exceptions_created{"
            'app_name="test",exception_type="ZeroDivisionError",method="GET",path="/error"}',
            'aiohttp_responses_total{app_name="test",method="GET",path="/error",status_code="500"} 1.0',
            'aiohttp_responses_created{app_name="test",method="GET",path="/error",status_code="500"}',
        )


async def test_json_response_handle(aiohttp_client: Callable) -> None:
    # Arrange
    expected_content_type = "text/plain; version=0.0.4; charset=utf-8"

    app = Application()
    app.router.add_get("/json_response", json_response_handler)

    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        openmetrics_format=False,
    )

    setup_metrics(app, metrics_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    json_response_ = await client.get("/json_response")
    response = await client.get("/metrics")
    # Assert
    assert response.status == 200
    assert json_response_.status == 200
    assert response.headers["content-type"] == expected_content_type
    assert_that(await response.text()).contains(
        'aiohttp_app_info{app_name="test"} 1.0',
        'aiohttp_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
        'aiohttp_requests_created{app_name="test",method="GET",path="/metrics"}',
        'aiohttp_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
    )


async def test_error_handle_with_tracing(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()
    app.router.add_get("/error", zero_division_handler)

    trace_cfg, exporter = build_aiohttp_tracing_config()
    metrics_cfg = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=False,
        include_trace_exemplar=True,
    )

    setup_metrics(app, metrics_cfg)
    setup_tracing(app, trace_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/error")
    # Assert
    span = exporter.get_finished_spans()[0]
    assert response.status == 500

    assert_that(span.events[0]._attributes).is_equal_to(
        {"exception.type": "ZeroDivisionError", "exception.message": "division by zero", "exception.escaped": "False"},
        ignore=["exception.stacktrace"],
    )


async def test_raise_handler_with_tracing(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()
    app.router.add_get("/raise_handler", raise_handler)

    trace_cfg, exporter = build_aiohttp_tracing_config()

    setup_tracing(app, trace_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/raise_handler")
    # Assert
    span = exporter.get_finished_spans()[0]
    assert response.status == 500

    assert_that(span.events[0]._attributes).is_equal_to(
        {
            "exception.type": "aiohttp.web_exceptions.HTTPInternalServerError",
            "exception.message": "Internal Server Error",
            "exception.escaped": "False",
        },
        ignore=["exception.stacktrace"],
    )


async def test_tracing(aiohttp_client: Callable) -> None:
    # Arrange
    app = Application()
    app.router.add_get("/", index_handler)

    trace_cfg, exporter = build_aiohttp_tracing_config()

    setup_tracing(app, trace_cfg)

    client: TestClient = await aiohttp_client(app)
    # Act
    response = await client.get("/")
    span = cast("tuple[Span, Span, Span]", exporter.get_finished_spans())
    assert_that(span[0].attributes).is_equal_to({
            'http.host': '0.0.0.0',
            'net.host.port': 80,
            'http.url': 'http://0.0.0.0',
            'http.status_code': 200
        }
    )
    assert response.status == 200
