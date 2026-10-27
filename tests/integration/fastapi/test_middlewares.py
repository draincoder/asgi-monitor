import asyncio
import re

import pytest
from assertpy import assert_that
from fastapi import APIRouter, FastAPI
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY

from asgi_monitor.integrations.fastapi import MetricsConfig, setup_metrics, setup_tracing
from asgi_monitor.metrics import get_latest_metrics
from tests.integration.factory import build_fastapi_tracing_config, fastapi_app

router = APIRouter(prefix="")


@router.get("/")
async def index() -> dict:
    await asyncio.sleep(0.1)
    return {"hello": "world"}


@router.get("/params/{param}")
async def one_parametrize(param: str) -> dict:
    return {"result": param}


@router.get("/params/{param_a}/{param_b}")
async def two_parametrize(param_a: str, param_b: str) -> dict:
    return {"result": [param_a, param_b]}


@pytest.mark.parametrize("accept_header", ["", "text/plain; version=1.0.0; escaping=underscores"])
async def test_metrics(accept_header: str) -> None:
    # Arrange
    expected_content_type = "text/plain; version=0.0.4; charset=utf-8"
    if accept_header and "version=1.0.0" in CONTENT_TYPE_LATEST:
        expected_content_type = f"{CONTENT_TYPE_LATEST}; escaping=underscores"
    app = FastAPI()
    metrics_config = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        openmetrics_format=False,
    )
    setup_metrics(app=app, config=metrics_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/metrics", headers={"Accept": accept_header})

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == expected_content_type
        assert_that(response.content.decode()).contains(
            'fastapi_app_info{app_name="test"} 1.0',
            'fastapi_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
            'fastapi_requests_created{app_name="test",method="GET",path="/metrics"}',
            'fastapi_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
        )


async def test_metrics_global_registry() -> None:
    # Arrange
    app = FastAPI()
    metrics_config = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=False,
        registry=REGISTRY,
    )
    setup_metrics(app=app, config=metrics_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert_that(response.content.decode()).contains(
            'fastapi_app_info{app_name="test"} 1.0',
            'fastapi_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
            'fastapi_requests_created{app_name="test",method="GET",path="/metrics"}',
            'fastapi_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
        )


@pytest.mark.parametrize(
    ("request_path", "expected_template"),
    [
        ("/", "/"),
        ("/params/one", "/params/{param}"),
        ("/params/one/two", "/params/{param_a}/{param_b}"),
    ],
)
@pytest.mark.parametrize("prefix", ["", "/api"])
@pytest.mark.parametrize("outer_prefix", ["", "/v1"])
async def test_metrics_with_tracing(request_path: str, expected_template: str, prefix: str, outer_prefix: str) -> None:
    # Arrange
    app = FastAPI()
    nested_router = APIRouter()
    nested_router.include_router(router, prefix=prefix)
    app.include_router(nested_router, prefix=outer_prefix)
    expected_template = outer_prefix + prefix + expected_template
    request_path = outer_prefix + prefix + request_path
    trace_config, exporter = build_fastapi_tracing_config()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=False, include_trace_exemplar=True)

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get(request_path)

        # Assert
        assert response.status_code == 200
        assert all(f"GET {expected_template}" in s.name for s in exporter.get_finished_spans())

        metrics = get_latest_metrics(metrics_config.registry, openmetrics_format=True)
        escaped_template = re.escape(expected_template)
        pattern = (
            r"fastapi_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="'
            + escaped_template
            + r'"}\ 1.0 # \{TraceID="(\w+)"\} (\d+(?:\.\d+)?(?:[eE][+-]?\d+)?) (\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
        )
        assert_that(metrics.payload.decode()).matches(pattern)
        assert_that(metrics.payload.decode()).contains('fastapi_app_info{app_name="test"} 1.0')


async def test_reused_router_prefixes() -> None:
    # Arrange
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.include_router(router, prefix="/v2")
    trace_config, exporter = build_fastapi_tracing_config()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=False, include_trace_exemplar=False)
    setup_metrics(app, metrics_config)
    setup_tracing(app, trace_config)

    # Act
    async with fastapi_app(app) as client:
        for path in ("/v1/params/one", "/v2/params/two", "/v1/params/three"):
            assert client.get(path).status_code == 200

    # Assert
    span_names = {span.name for span in exporter.get_finished_spans()}
    assert {"GET /v1/params/{param}", "GET /v2/params/{param}"} <= span_names
    metrics = get_latest_metrics(metrics_config.registry, openmetrics_format=False)
    assert_that(metrics.payload.decode()).contains(
        'fastapi_requests_total{app_name="test",method="GET",path="/v1/params/{param}"} 2.0',
        'fastapi_requests_total{app_name="test",method="GET",path="/v2/params/{param}"} 1.0',
    )


async def test_single_server_span(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    app = FastAPI()
    app.include_router(router, prefix="/api")
    trace_config, exporter = build_fastapi_tracing_config()
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", trace_config.tracer_provider)
    setup_tracing(app, trace_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/api/params/one")

    # Assert
    assert response.status_code == 200
    server_spans = [span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER]
    assert len(server_spans) == 1
    assert server_spans[0].name == "GET /api/params/{param}"
    assert server_spans[0].attributes is not None
    assert server_spans[0].attributes["http.route"] == "/api/params/{param}"


@pytest.mark.parametrize(
    ("method", "path", "status_code", "expected_route"),
    [
        ("GET", "/api/missing", 404, None),
        ("POST", "/api/params/one", 405, "/api/params/{param}"),
    ],
)
async def test_unmatched_router_requests(method: str, path: str, status_code: int, expected_route: str | None) -> None:
    # Arrange
    app = FastAPI()
    app.include_router(router, prefix="/api")
    trace_config, exporter = build_fastapi_tracing_config()
    setup_metrics(app, MetricsConfig(app_name="test", include_metrics_endpoint=False))
    setup_tracing(app, trace_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.request(method, path)

    # Assert
    assert response.status_code == status_code
    server_spans = [span for span in exporter.get_finished_spans() if span.kind == SpanKind.SERVER]
    assert len(server_spans) == 1
    assert server_spans[0].attributes is not None
    assert server_spans[0].attributes.get("http.route") == expected_route


async def test_metrics_openmetrics_with_tracing() -> None:
    # Arrange
    expected_content_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
    app = FastAPI()
    app.include_router(router)
    trace_config, _ = build_fastapi_tracing_config()
    metrics_config = MetricsConfig(
        app_name="test",
        include_metrics_endpoint=True,
        include_trace_exemplar=True,
        openmetrics_format=True,
    )

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/")
        metrics = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert metrics.status_code == 200
        assert metrics.headers["content-type"] == expected_content_type
        pattern = (
            r"fastapi_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} '
            r"(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?) (\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
        )
        assert_that(metrics.content.decode()).matches(pattern)
        assert_that(metrics.content.decode()).contains('fastapi_app_info{app_name="test"} 1.0')


async def test_metrics_get_path() -> None:
    # Arrange
    app = FastAPI()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=True, include_trace_exemplar=False)
    setup_metrics(app=app, config=metrics_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/metrics/")

        # Assert
        assert response.status_code == 200
        assert_that(response.content.decode()).contains(
            'fastapi_app_info{app_name="test"} 1.0',
            'fastapi_requests_total{app_name="test",method="GET",path="/metrics"} 1.0',
            'fastapi_requests_created{app_name="test",method="GET",path="/metrics"}',
            'fastapi_requests_in_progress{app_name="test",method="GET",path="/metrics"} 1.0',
        )
