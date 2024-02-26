import logging

from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.gunicorn import GunicornStandaloneApplication, StubbedGunicornLogger
from .asgi_app import get_app


def run() -> None:
    level = logging.DEBUG
    json_format = False
    configure_logging(level=level, json_format=json_format)
    worker_class = "asgi_monitor.logging.uvicorn.worker.StructlogUvicornWorker"
    options = {
        "bind": "127.0.0.1",
        "workers": 1,
        "loglevel": logging.getLevelName(level),
        "worker_class": worker_class,
        "logger_class": StubbedGunicornLogger,
    }

    app = get_app()

    GunicornStandaloneApplication(app, options).run()


if __name__ == "__main__":
    run()
