import asyncio

from assertpy import assert_that
from fastapi import APIRouter, FastAPI
from prometheus_client import REGISTRY

from asgi_monitor.integrations.fastapi import MetricsConfig, setup_metrics, setup_tracing
from asgi_monitor.metrics import get_latest_metrics
from tests.integration.factory import build_fastapi_tracing_config, fastapi_app

router = APIRouter(prefix="")


@router.get("/")
async def index() -> dict:
    await asyncio.sleep(0.1)
    return {"hello": "world"}


async def test_metrics() -> None:
    # Arrange
    app = FastAPI()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=True, include_trace_exemplar=False)
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


async def test_metrics_with_tracing() -> None:
    # Arrange
    app = FastAPI()
    app.include_router(router)
    trace_config, _ = build_fastapi_tracing_config()
    metrics_config = MetricsConfig(app_name="test", include_metrics_endpoint=False, include_trace_exemplar=True)

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        metrics = get_latest_metrics(metrics_config.registry, openmetrics_format=True)
        pattern = (
            r"fastapi_request_duration_seconds_bucket\{"
            r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
        )
        assert_that(metrics.payload.decode()).matches(pattern)
        assert_that(metrics.payload.decode()).contains('fastapi_app_info{app_name="test"} 1.0')


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
