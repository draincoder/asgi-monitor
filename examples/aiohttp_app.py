import asyncio
import logging
from datetime import datetime, timezone

from aiohttp.web import Application, Request, Response, run_app
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from asgi_monitor.integrations.aiohttp import MetricsConfig, TracingConfig, setup_metrics, setup_tracing
from asgi_monitor.logging import configure_logging

logger = logging.getLogger(__name__)


async def index(requests: Request) -> Response:
    logger.info("Start sleeping at %s", datetime.now(tz=timezone.utc))
    await asyncio.sleep(1)
    logger.info("Stopped sleeping at %s", datetime.now(tz=timezone.utc))
    return Response(text="OK")


def create_app() -> Application:
    configure_logging(json_format=True, include_trace=False)

    app = Application()
    app.router.add_get("/", index)

    resource = Resource.create(
        attributes={
            "service.name": "aiohttp",
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    trace_config = TracingConfig(tracer_provider=tracer_provider)
    metrics_config = MetricsConfig(app_name="fastapi", include_trace_exemplar=True)

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)

    return app


if __name__ == "__main__":
    app = create_app()
    run_app(app=app, host="127.0.0.1", port=8000)
