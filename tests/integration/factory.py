import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

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

from asgi_monitor.integrations.aiohttp import TracingConfig as AioHTTPTraceConfig
from asgi_monitor.integrations.fastapi import TracingConfig as FastAPITraceConfig
from asgi_monitor.integrations.litestar import TracingConfig as LitestarTraceConfig
from asgi_monitor.integrations.starlette import TracingConfig as StarletteTraceConfig


@asynccontextmanager
async def starlette_app(app: Starlette) -> AsyncIterator[TestClient]:
    yield TestClient(app)


@asynccontextmanager
async def fastapi_app(app: FastAPI) -> AsyncIterator[TestClient]:
    yield TestClient(app)


@asynccontextmanager
async def litestar_app(app: Litestar) -> AsyncIterator[LitestarTestClient]:
    yield LitestarTestClient(app)


@asynccontextmanager
async def run_server(config: Config) -> AsyncIterator[Server]:
    server = Server(config=config)
    task = asyncio.create_task(server.serve())

    try:
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("Uvicorn stopped before startup")
                await asyncio.sleep(0.01)
        yield server
    finally:
        if server.started:
            await server.shutdown()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def build_fastapi_tracing_config() -> tuple[FastAPITraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "fastapi",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    return FastAPITraceConfig(tracer_provider=tracer_provider), exporter


def build_starlette_tracing_config() -> tuple[StarletteTraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "starlette",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    return StarletteTraceConfig(tracer_provider=tracer_provider), exporter


def build_litestar_tracing_config() -> tuple[LitestarTraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "litestar",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    return LitestarTraceConfig(tracer_provider=tracer_provider), exporter


def build_aiohttp_tracing_config() -> tuple[AioHTTPTraceConfig, InMemorySpanExporter]:
    resource = Resource.create(
        attributes={
            "service.name": "aiohttp",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    exporter = InMemorySpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    return AioHTTPTraceConfig(tracer_provider=tracer_provider), exporter
