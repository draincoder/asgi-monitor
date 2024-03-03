import logging
from typing import Any

import pytest
from fastapi import FastAPI

from asgi_monitor.logging.gunicorn import GunicornStandaloneApplication, StubbedGunicornLogger
from asgi_monitor.logging.uvicorn.worker import (
    StructlogJSONLogUvicornWorker,
    StructlogTextLogUvicornWorker,
    StructlogTraceJSONLogUvicornWorker,
    StructlogTraceTextLogUvicornWorker,
)


def gunicorn_app(worker_class: str) -> GunicornStandaloneApplication:
    app = FastAPI()
    level = logging.DEBUG
    options = {
        "bind": "127.0.0.1",
        "workers": 1,
        "loglevel": logging.getLevelName(level),
        "worker_class": worker_class,
        "logger_class": StubbedGunicornLogger,
    }
    return GunicornStandaloneApplication(app, options)


@pytest.mark.parametrize(
    ("worker", "expected"),
    [
        ("StructlogTextLogUvicornWorker", StructlogTextLogUvicornWorker),
        ("StructlogTraceTextLogUvicornWorker", StructlogTraceTextLogUvicornWorker),
        ("StructlogJSONLogUvicornWorker", StructlogJSONLogUvicornWorker),
        ("StructlogTraceJSONLogUvicornWorker", StructlogTraceJSONLogUvicornWorker),
    ],
)
def test_uvicorn_text_worker(worker: str, expected: Any) -> None:
    # Assert
    worker_class = f"asgi_monitor.logging.uvicorn.worker.{worker}"

    # Act
    gunicorn = gunicorn_app(worker_class)
    gunicorn.load()

    # Assert
    assert gunicorn.cfg.worker_class == expected
