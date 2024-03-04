from fastapi import FastAPI

from .error import error_router
from .healthcheck import healthcheck_router
from .slow import slow_router

__all__ = ("setup_routes",)


def setup_routes(app: FastAPI) -> None:
    app.include_router(healthcheck_router)
    app.include_router(error_router)
    app.include_router(slow_router)
