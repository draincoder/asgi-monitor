import logging
import sys

import structlog

from ._default_processors import _build_default_processors
from .trace_processor import extract_opentelemetry_trace_meta

__all__ = ("configure_logging",)


def configure_logging(
    level: str | int = logging.INFO,
    *,
    json_format: bool,
    include_trace: bool,
) -> None:
    """
    Default logging setting for logging and structlog.

    :param str | int level: Logging level.
    :param bool json_format: The format of the logs. If True, the log will be rendered as JSON.
    :param bool include_trace: Include tracing information ("trace_id", "span_id", "parent_span_id", "service.name").
    :returns: None
    """

    _configure_structlog(json_format=json_format, include_trace=include_trace)
    _configure_default_logging(level=level, json_format=json_format, include_trace=include_trace)


def _configure_structlog(
    *,
    json_format: bool,
    include_trace: bool,
) -> None:
    processors = [
        *_build_default_processors(json_format=json_format),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.UnicodeDecoder(),  # convert bytes to str
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # for integration with default logging
    ]

    if include_trace:
        processors.insert(-1, extract_opentelemetry_trace_meta)  # after defaults

    structlog.configure_once(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _configure_default_logging(
    *,
    level: str | int,
    json_format: bool,
    include_trace: bool,
) -> None:
    renderer_processor = structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer()
    default_processors = _build_default_processors(json_format=json_format)

    if include_trace:
        default_processors.append(extract_opentelemetry_trace_meta)  # after defaults

    logging_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        renderer_processor,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=default_processors,
        processors=logging_processors,  # type: ignore[arg-type]
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.set_name("default")
    handler.setLevel(level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
