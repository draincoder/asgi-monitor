import asyncio
import logging
from datetime import datetime, timezone

import uvicorn
from fastapi import APIRouter, FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from asgi_monitor.integrations.fastapi import MetricsConfig, TracingConfig, setup_metrics, setup_tracing
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="")


@router.get("/")
async def index() -> str:
    logger.info("Start sleeping at %s", datetime.now(tz=timezone.utc))
    await asyncio.sleep(1)
    logger.info("Stopped sleeping at %s", datetime.now(tz=timezone.utc))
    return "OK"


def create_app() -> FastAPI:
    configure_logging(level=logging.INFO, json_format=True, include_trace=False)

    resource = Resource.create(
        attributes={
            "service.name": "fastapi",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    trace_config = TracingConfig(tracer_provider=tracer_provider)
    metrics_config = MetricsConfig(app_name="fastapi", include_trace_exemplar=True)

    app = FastAPI(debug=True)
    app.include_router(router)

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    return app


if __name__ == "__main__":
    log_config = build_uvicorn_log_config(
        level=logging.INFO,
        json_format=True,
        include_trace=True,
    )
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)
