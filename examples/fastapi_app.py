import asyncio
import logging
from datetime import datetime, timezone

import uvicorn
from fastapi import APIRouter, FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from asgi_monitor.integrations.fastapi import TracingConfig, setup_metrics, setup_tracing
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
    configure_logging(level=logging.INFO, json_format=True)

    resource = Resource.create(
        attributes={
            "service.name": "fastapi",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    config = TracingConfig(tracer_provider=tracer)

    app = FastAPI(debug=True)
    app.include_router(router)
    setup_tracing(app=app, config=config)
    setup_metrics(app, app_name="fastapi", include_trace=True, include_metrics_endpoint=True)

    return app


if __name__ == "__main__":
    log_config = build_uvicorn_log_config(
        level=logging.INFO,
        json_format=True,
        include_trace=True,
    )
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)
