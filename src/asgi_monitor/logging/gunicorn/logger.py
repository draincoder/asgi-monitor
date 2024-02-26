import logging

from gunicorn.config import Config
from gunicorn.glogging import Logger

__all__ = ("StubbedGunicornLogger",)


class StubbedGunicornLogger(Logger):
    def setup(self, cfg: Config) -> None:
        _name_to_level = {
            "CRITICAL": logging.CRITICAL,
            "FATAL": logging.FATAL,
            "ERROR": logging.ERROR,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }

        self.loglevel = _name_to_level[cfg.loglevel]
        self.error_log.setLevel(self.loglevel)
        self.access_log.setLevel(self.loglevel)
