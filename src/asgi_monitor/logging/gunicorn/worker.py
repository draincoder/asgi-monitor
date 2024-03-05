from typing import Any

from gunicorn.app.base import BaseApplication

__all__ = ("GunicornStandaloneApplication",)


class GunicornStandaloneApplication(BaseApplication):
    """
    Custom standalone application class for running a Gunicorn server with a ASGI application using Uvicorn worker.
    """

    def __init__(
        self,
        app: Any,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        c = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in c.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> Any:
        return self.application
