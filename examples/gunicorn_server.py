import logging

from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.gunicorn import GunicornStandaloneApplication, StubbedGunicornLogger


def run() -> None:
    level = logging.DEBUG
    worker_class = "asgi_monitor.logging.uvicorn.worker.StructlogJSONLogUvicornWorker"
    options = {
        "bind": "127.0.0.1",
        "workers": 1,
        "loglevel": logging.getLevelName(level),
        "worker_class": worker_class,
        "logger_class": StubbedGunicornLogger,
    }
    configure_logging(level=level, json_format=True)

    from examples.asgi_app import get_app

    app = get_app()

    GunicornStandaloneApplication(app, options).run()


if __name__ == "__main__":
    run()
