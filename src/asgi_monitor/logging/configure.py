import logging
import sys

import structlog

from ._processors import _build_default_processors

__all__ = ("configure_logging",)


def configure_logging(level: str | int = logging.INFO, json_format: bool = False) -> None:
    _configure_structlog(json_format)
    _configure_default_logging(level=level, json_format=json_format)


def _configure_structlog(json_format: bool) -> None:
    structlog.configure_once(
        processors=[
            *_build_default_processors(json_format=json_format),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # for integration with default logging
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _configure_default_logging(*, level: str | int, json_format: bool) -> None:
    renderer_processor = structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            *_build_default_processors(json_format=json_format),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer_processor,
        ],
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
