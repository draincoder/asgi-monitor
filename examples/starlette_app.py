import asyncio
import logging
from datetime import datetime, timezone

import uvicorn
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from asgi_monitor.integrations.starlette import TracingConfig, setup_monitoring
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

logger = logging.getLogger(__name__)


async def index(_: Request) -> PlainTextResponse:
    logger.info("Start sleeping at %s", datetime.now(tz=timezone.utc))
    await asyncio.sleep(1)
    logger.info("Stopped sleeping at %s", datetime.now(tz=timezone.utc))
    return PlainTextResponse("OK")


def create_app() -> Starlette:
    configure_logging(level=logging.INFO, json_format=True)

    resource = Resource.create(
        attributes={
            "service.name": "starlette",
        },
    )
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)
    config = TracingConfig(tracer_provider=tracer)

    app = Starlette(debug=True, routes=[Route("/", endpoint=index, methods=["GET"])])
    setup_monitoring(app=app, config=config)

    return app


if __name__ == "__main__":
    log_config = build_uvicorn_log_config(
        level=logging.INFO,
        json_format=True,
        include_trace=True,
    )
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_config=log_config)
