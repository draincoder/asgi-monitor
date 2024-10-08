import logging

import uvicorn
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from asgi_monitor.integrations.fastapi import MetricsConfig, TracingConfig, setup_metrics, setup_tracing
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

from app.routes import setup_routes

logger = logging.getLogger(__name__)

APP_NAME = "asgi-monitor"
HOST = "0.0.0.0"
PORT = 8080
GRPC_ENDPOINT = "http://asgi-monitor.tempo:4317"


def create_app() -> FastAPI:
    configure_logging(level=logging.INFO, json_format=True, include_trace=True)

    resource = Resource.create(
        attributes={
            "service.name": APP_NAME,
            "compose_service": APP_NAME,
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=GRPC_ENDPOINT)))

    trace_config = TracingConfig(tracer_provider=tracer_provider)
    metrics_config = MetricsConfig(app_name=APP_NAME, include_trace_exemplar=True)

    app = FastAPI(debug=True)

    setup_metrics(app=app, config=metrics_config)
    setup_tracing(app=app, config=trace_config)
    setup_routes(app=app)

    return app


if __name__ == "__main__":
    log_config = build_uvicorn_log_config(
        level=logging.INFO,
        json_format=True,
        include_trace=True,
    )
    uvicorn.run(create_app(), host=HOST, port=PORT, log_config=log_config)
