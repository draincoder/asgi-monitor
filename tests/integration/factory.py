import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from litestar import Litestar
from litestar.testing import TestClient as LitestarTestClient
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from starlette.applications import Starlette
from starlette.testclient import TestClient
from uvicorn import Config, Server

from asgi_monitor.integrations.fastapi import TracingConfig as FastAPITraceConfig
from asgi_monitor.integrations.litestar import TracingConfig as LitestarTraceConfig
from asgi_monitor.integrations.starlette import TracingConfig as StarletteTraceConfig


@asynccontextmanager
async def starlette_app(app: Starlette) -> AsyncIterator[TestClient]:
    async with LifespanManager(app):
        yield TestClient(app)


@asynccontextmanager
async def fastapi_app(app: FastAPI) -> AsyncIterator[TestClient]:
    async with LifespanManager(app):
        yield TestClient(app)


@asynccontextmanager
async def litestar_app(app: Litestar) -> AsyncIterator[LitestarTestClient]:
    async with LifespanManager(app):
        yield LitestarTestClient(app)


@asynccontextmanager
async def run_server(config: Config) -> AsyncIterator[Server]:
    server = Server(config=config)
    task = asyncio.create_task(server.serve())

    await asyncio.sleep(0.1)

    try:
        yield server
    finally:
        await server.shutdown()
        task.cancel()


def build_fastapi_tracing_config() -> tuple[FastAPITraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "fastapi",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    exporter = InMemorySpanExporter()
    tracer.add_span_processor(SimpleSpanProcessor(exporter))

    return FastAPITraceConfig(tracer_provider=tracer), exporter


def build_starlette_tracing_config() -> tuple[StarletteTraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "starlette",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    exporter = InMemorySpanExporter()
    tracer.add_span_processor(SimpleSpanProcessor(exporter))

    return StarletteTraceConfig(tracer_provider=tracer), exporter


def build_litestar_tracing_config() -> tuple[LitestarTraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "litestar",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    exporter = InMemorySpanExporter()
    tracer.add_span_processor(SimpleSpanProcessor(exporter))

    return LitestarTraceConfig(tracer_provider=tracer), exporter
