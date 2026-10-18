from typing import Any

from fastapi import FastAPI
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span
from starlette.types import Message, Receive, Scope, Send

from asgi_monitor.tracing import BaseTracingConfig
from asgi_monitor.tracing.middleware import build_open_telemetry_middleware


def test_build_middleware() -> None:
    # Arrange
    app = FastAPI()
    tracer = TracerProvider()

    def default_extractor(scope: Any) -> tuple[str, dict[str, Any]]:
        return "test", {"test": "test"}

    # Act
    config = BaseTracingConfig(
        exclude_urls_env_key="FASTAPI",
        scope_span_details_extractor=default_extractor,
        tracer_provider=tracer,
    )
    middleware = build_open_telemetry_middleware(app, config)

    # Assert
    assert isinstance(middleware, OpenTelemetryMiddleware)


async def test_client_hooks_receive_scope_and_message(tracer_provider: TracerProvider) -> None:
    # Arrange
    request_events: list[tuple[str, str]] = []
    response_events: list[tuple[str, str]] = []

    def request_hook(span: Span, scope: dict[str, Any], message: dict[str, Any]) -> None:
        assert span.is_recording()
        request_events.append((scope["type"], message["type"]))

    def response_hook(span: Span, scope: dict[str, Any], message: dict[str, Any]) -> None:
        assert span.is_recording()
        response_events.append((scope["type"], message["type"]))

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        pass

    config = BaseTracingConfig(
        exclude_urls_env_key="ASGI",
        scope_span_details_extractor=lambda scope: ("test", {}),
        tracer_provider=tracer_provider,
        client_request_hook_handler=request_hook,
        client_response_hook_handler=response_hook,
    )
    middleware = build_open_telemetry_middleware(app, config)
    scope: Scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 80),
    }

    # Act
    await middleware(scope, receive, send)

    # Assert
    assert request_events == [("http", "http.request")]
    assert response_events == [("http", "http.response.start"), ("http", "http.response.body")]
