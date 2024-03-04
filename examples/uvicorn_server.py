import logging

import uvicorn

from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config


def run() -> None:
    level = logging.DEBUG
    json_format = False
    log_config = build_uvicorn_log_config(level=level, json_format=json_format, include_trace=False)
    configure_logging(level=level, json_format=json_format)

    from asgi_app import get_app

    app = get_app()

    uvicorn.run(app=app, log_config=log_config, use_colors=False)


if __name__ == "__main__":
    run()
