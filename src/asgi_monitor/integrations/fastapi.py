from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from fastapi import FastAPI

from asgi_monitor.integrations.starlette import TracingMiddleware, _get_default_span_details

__all__ = ("TracingConfig", "TracingMiddleware", "setup_monitoring")

from asgi_monitor.tracing import _TracingConfig


@dataclass
class TracingConfig(_TracingConfig):
    exclude_urls_env_key: str = "FASTAPI"
    scope_span_details_extractor: Callable[[Any], tuple[str, dict[str, Any]]] = _get_default_span_details


def setup_monitoring(app: FastAPI, config: TracingConfig) -> None:
    app.add_middleware(TracingMiddleware, config=config)
