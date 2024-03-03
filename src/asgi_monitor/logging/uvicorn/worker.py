import logging
from typing import Any

from uvicorn.workers import UvicornWorker

from .log_config import build_uvicorn_log_config

__all__ = (
    "StructlogTextLogUvicornWorker",
    "StructlogTraceTextLogUvicornWorker",
    "StructlogJSONLogUvicornWorker",
    "StructlogTraceJSONLogUvicornWorker",
)


class StructlogDefaultUvicornWorker(UvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = False
    include_trace: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.CONFIG_KWARGS["log_config"] = build_uvicorn_log_config(
            level=self.level,
            json_format=self.json_format,
            include_trace=self.include_trace,
        )
        super().__init__(*args, **kwargs)


class StructlogTextLogUvicornWorker(StructlogDefaultUvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = False
    include_trace: bool = False


class StructlogTraceTextLogUvicornWorker(StructlogDefaultUvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = False
    include_trace: bool = True


class StructlogJSONLogUvicornWorker(StructlogDefaultUvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = True
    include_trace: bool = False


class StructlogTraceJSONLogUvicornWorker(StructlogDefaultUvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = True
    include_trace: bool = True
