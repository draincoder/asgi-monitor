from typing import Any

from fastapi import FastAPI
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import TracerProvider

from asgi_monitor.tracing import TracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware


def test_build_middleware() -> None:
    # Arrange
    app = FastAPI()
    tracer = TracerProvider()

    def default_extractor(scope: Any) -> tuple[str, dict[str, Any]]:
        return "test", {"test": "test"}

    # Act
    config = TracingConfig(
        exclude_urls_env_key="FASTAPI",
        scope_span_details_extractor=default_extractor,
        tracer_provider=tracer,
    )
    middleware = build_open_telemetry_middleware(app, config)

    # Assert
    assert isinstance(middleware, OpenTelemetryMiddleware)
