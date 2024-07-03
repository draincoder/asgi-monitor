import contextlib
import logging
from typing import Any

import structlog

from asgi_monitor.logging._default_processors import _build_default_processors
from asgi_monitor.logging.trace_processor import extract_opentelemetry_trace_meta

__all__ = ("build_uvicorn_log_config",)


def _extract_uvicorn_request_meta(
    wrapped_logger: logging.Logger | None,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    with contextlib.suppress(KeyError, ValueError):
        (
            client_addr,
            method,
            full_path,
            http_version,
            status_code,
        ) = event_dict["positional_args"]

        event_dict["client_addr"] = client_addr
        event_dict["http_method"] = method
        event_dict["url"] = full_path
        event_dict["http_version"] = http_version
        event_dict["status_code"] = status_code

        del event_dict["positional_args"]

    return event_dict


class UvicornDefaultConsoleFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=_build_default_processors(json_format=False),
        )


class UvicornAccessConsoleFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        processors = [
            _extract_uvicorn_request_meta,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ]

        super().__init__(
            processors=processors,  # type: ignore[arg-type]
            foreign_pre_chain=_build_default_processors(json_format=False),
            pass_foreign_args=True,  # for args from record.args in positional_args
        )


class TraceUvicornAccessConsoleFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        processors = [
            _extract_uvicorn_request_meta,
            extract_opentelemetry_trace_meta,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ]

        super().__init__(
            processors=processors,  # type: ignore[arg-type]
            foreign_pre_chain=_build_default_processors(json_format=False),
            pass_foreign_args=True,  # for args from record.args in positional_args
        )


class UvicornDefaultJSONFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=_build_default_processors(json_format=True),
        )


class UvicornAccessJSONFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        processors = [
            _extract_uvicorn_request_meta,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ]

        super().__init__(
            processors=processors,  # type: ignore[arg-type]
            foreign_pre_chain=_build_default_processors(json_format=True),
            pass_foreign_args=True,  # for args from record.args in positional_args
        )


class TraceUvicornAccessJSONFormatter(structlog.stdlib.ProcessorFormatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        processors = [
            _extract_uvicorn_request_meta,
            extract_opentelemetry_trace_meta,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ]

        super().__init__(
            processors=processors,  # type: ignore[arg-type]
            foreign_pre_chain=_build_default_processors(json_format=True),
            pass_foreign_args=True,  # for args from record.args in positional_args
        )


def build_uvicorn_log_config(
    level: str | int = logging.INFO,
    *,
    json_format: bool,
    include_trace: bool,
) -> dict[str, Any]:
    """
    Building a Uvicorn log config.

    :param str | int level: Logging level.
    :param bool json_format: The format of the logs. If True, the log will be rendered as JSON.
    :param bool include_trace: Include tracing information ("trace_id", "span_id", "parent_span_id", "service.name").
    :returns: Logging configuration for Uvicorn
    """

    level_name = logging.getLevelName(level)

    if json_format:
        default = UvicornDefaultJSONFormatter
        access = UvicornAccessJSONFormatter if not include_trace else TraceUvicornAccessJSONFormatter
    else:
        default = UvicornDefaultConsoleFormatter  # type: ignore[assignment]
        access = UvicornAccessConsoleFormatter if not include_trace else TraceUvicornAccessConsoleFormatter

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": f"{default.__module__}.{default.__name__}",
            },
            "access": {
                "()": f"{access.__module__}.{access.__name__}",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": level_name,
                "propagate": False,
            },
            "uvicorn.error": {
                "level": level_name,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": level_name,
                "propagate": False,
            },
        },
    }
