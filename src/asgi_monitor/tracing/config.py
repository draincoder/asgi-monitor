# https://github.com/open-telemetry/opentelemetry-python-contrib/blob/main/instrumentation/opentelemetry-instrumentation-fastapi/src/opentelemetry/instrumentation/fastapi/__init__.py
# https://github.com/litestar-org/litestar/blob/main/litestar/contrib/opentelemetry/config.py
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = ("BaseTracingConfig",)


from opentelemetry.metrics import Meter, MeterProvider
from opentelemetry.trace import Span, TracerProvider

OpenTelemetryHookHandler = Callable[[Span, dict[str, Any], dict[str, Any]], None]


@dataclass(slots=True, frozen=True)
class BaseTracingConfig:
    """
    Configuration class for the OpenTelemetry middleware.
    Consult the OpenTelemetry ASGI documentation for more info about the configuration options.
    https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html
    """

    exclude_urls_env_key: str
    """
    Key to use when checking whether a list of excluded urls is passed via ENV.
    OpenTelemetry supports excluding urls by passing an env in the format '{exclude_urls_env_key}_EXCLUDED_URLS'.
    """

    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]]
    """
    Callback which should return a string and a tuple, representing the desired default span name and a dictionary
    with any additional span attributes to set.
    """

    server_request_hook_handler: Callable[[Span, dict[str, Any]], None] | None = field(default=None)
    """Optional callback which is called with the server span and ASGI scope object for every incoming request."""

    client_request_hook_handler: OpenTelemetryHookHandler | None = field(default=None)
    """
    Optional callback which is called with the internal span and an ASGI scope which is sent as a dictionary for when
    the method receive is called.
    """

    client_response_hook_handler: OpenTelemetryHookHandler | None = field(default=None)
    """
    Optional callback which is called with the internal span and an ASGI event which is sent as a dictionary for when
    the method send is called.
    """

    meter_provider: MeterProvider | None = field(default=None)
    """Optional meter provider to use."""

    tracer_provider: TracerProvider | None = field(default=None)
    """Optional tracer provider to use."""

    meter: Meter | None = field(default=None)
    """Optional meter to use."""
