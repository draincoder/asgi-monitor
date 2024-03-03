from contextlib import asynccontextmanager

from asgi_lifespan import LifespanManager
from assertpy import assert_that
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from asgi_monitor.integrations.fastapi import TracingConfig, setup_metrics, setup_tracing
from asgi_monitor.metrics import get_latest_metrics

router = APIRouter(prefix="")


@asynccontextmanager
async def fastapi_app(app: FastAPI) -> TestClient:
    async with LifespanManager(app):
        yield TestClient(app)


def build_tracing_config() -> tuple[TracingConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "fastapi",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    exporter = InMemorySpanExporter()
    tracer.add_span_processor(SimpleSpanProcessor(exporter))
    return TracingConfig(tracer_provider=tracer), exporter


@router.get("/")
async def index() -> dict:
    return {"hello": "world"}


async def test_metrics_middleware() -> None:
    # Arrange
    app = FastAPI()
    setup_metrics(app=app, app_name="test")

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/metrics")

        # Assert
        assert response.status_code == 200
        assert_that(response.content.decode()).contains(
            'fastapi_app_info{app_name="test"} 1.0',
            'fastapi_requests_total{app_name="test",method="GET",path="/metrics/"} 1.0',
            'fastapi_requests_created{app_name="test",method="GET",path="/metrics/"}',
            'fastapi_requests_in_progress{app_name="test",method="GET",path="/metrics/"} 1.0',
        )


async def test_full_middleware() -> None:
    # Arrange
    config, _ = build_tracing_config()
    app = FastAPI()
    app.include_router(router)
    setup_metrics(app=app, app_name="test", include_metrics_endpoint=False, include_trace=True)
    setup_tracing(app=app, config=config)
    pattern = (
        r"fastapi_request_duration_seconds_bucket\{"
        r'app_name="test",le="([\d.]+)",method="GET",path="\/"}\ 1.0 # \{TraceID="(\w+)"\} (\d+\.\d+) (\d+\.\d+)'
    )

    # Act
    async with fastapi_app(app) as client:
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        metrics = get_latest_metrics(openmetrics_format=True)
        assert_that(metrics.payload.decode()).matches(pattern)
