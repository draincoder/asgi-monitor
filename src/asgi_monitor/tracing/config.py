# https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-fastapi/src/opentelemetry/instrumentation/fastapi/__init__.py
# https://github.com/litestar-org/litestar/blob/main/litestar/contrib/opentelemetry/config.py
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ("CommonTracingConfig",)


from opentelemetry.metrics import Meter, MeterProvider
from opentelemetry.trace import Span, TracerProvider

OpenTelemetryHookHandler = Callable[[Span, dict], None]


@dataclass
class CommonTracingConfig:
    exclude_urls_env_key: str
    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]]
    server_request_hook_handler: OpenTelemetryHookHandler | None = field(default=None)
    client_request_hook_handler: OpenTelemetryHookHandler | None = field(default=None)
    client_response_hook_handler: OpenTelemetryHookHandler | None = field(default=None)
    meter_provider: MeterProvider | None = field(default=None)
    tracer_provider: TracerProvider | None = field(default=None)
    meter: Meter | None = field(default=None)
