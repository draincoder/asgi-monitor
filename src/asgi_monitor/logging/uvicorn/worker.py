import logging
from typing import Any

from uvicorn.workers import UvicornWorker

from .log_config import build_uvicorn_log_config

__all__ = ("StructlogUvicornWorker",)


class StructlogUvicornWorker(UvicornWorker):
    level: int = logging.DEBUG
    json_format: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.CONFIG_KWARGS["log_config"] = build_uvicorn_log_config(
            level=self.level,
            json_format=self.json_format,
        )
        super().__init__(*args, **kwargs)
