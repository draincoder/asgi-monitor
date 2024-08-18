import asyncio
import logging
from datetime import datetime, timezone

import uvicorn
from litestar import Litestar, get
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from asgi_monitor.integrations.litestar import (
    MetricsConfig,
    TracingConfig,
    add_metrics_endpoint,
    build_metrics_middleware,
    build_tracing_middleware,
)
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

logger = logging.getLogger(__name__)


@get("/")
async def index() -> str:
    logger.info("Start sleeping at %s", datetime.now(tz=timezone.utc))
    await asyncio.sleep(1)
    logger.info("Stopped sleeping at %s", datetime.now(tz=timezone.utc))
    return "OK"


def create_app() -> Litestar:
    configure_logging(level=logging.INFO, json_format=True, include_trace=False)

    resource = Resource.create(
        attributes={
            "service.name": "litestar",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    trace_config = TracingConfig(tracer_provider=tracer_provider)
    metrics_config = MetricsConfig(app_name="litestar", include_trace_exemplar=True)
    middlewares = [build_tracing_middleware(trace_config), build_metrics_middleware(metrics_config)]

    app = Litestar([index], middleware=middlewares, logging_config=None)

    add_metrics_endpoint(app, metrics_config.registry, openmetrics_format=False)

    return app


if __name__ == "__main__":
    log_config = build_uvicorn_log_config(
        level=logging.INFO,
        json_format=True,
        include_trace=True,
    )
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)
