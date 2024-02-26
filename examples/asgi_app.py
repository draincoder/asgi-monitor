import asyncio
import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from threading import Thread
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

structlog_logger = structlog.stdlib.get_logger("structlog")
default_logger = logging.getLogger("default_logger")
request_id: ContextVar[str] = ContextVar("request_id")

default_logger.warning("log in module")


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    value = request.headers.get("request-id", str(uuid.uuid4()))

    request_id.set(value)

    structlog_logger.debug("extract request id header", request_id=value)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=value)

    response: Response = await call_next(request)

    return response


async def log(q: str | None = None) -> Any:
    default_logger.info("processing request", extra={"q": q, "request_id": request_id.get()})

    async def create_task() -> None:
        default_logger.warning("processing task")

    task = asyncio.create_task(create_task())

    def sum_numbers(numbers: list[int]) -> None:
        result = sum(numbers)
        default_logger.warning("numbers sum", extra={"result": result})

    t = Thread(target=sum_numbers, args=(list(range(5)),))
    t.start()

    await task

    t.join()

    return "pong"


async def slog(q: str | None = None) -> Any:
    structlog_logger.info("processing request", q=q)

    async def create_task() -> None:
        structlog_logger.debug("processing task")

    task = asyncio.create_task(create_task())

    def sum_numbers(numbers: list[int]) -> None:
        result = sum(numbers)
        structlog_logger.debug("numbers sum", result=result)

    t = Thread(target=sum_numbers, args=(list(range(5)),))
    t.start()

    await task

    t.join()

    return "pong"


async def exc() -> Any:
    print(logging.getLogger("uvicorn.error").handlers)
    print(logging.getLogger("uvicorn.error").handlers[0].formatter)
    raise RuntimeError("+inf")


async def error() -> Any:
    try:
        1 / 0
    except ZeroDivisionError:
        default_logger.exception("+inf")


def get_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)
    app.add_api_route("/log", log, response_class=PlainTextResponse, methods=["GET"])
    app.add_api_route("/slog", slog, response_class=PlainTextResponse, methods=["GET"])
    app.add_api_route("/exc", exc, response_class=PlainTextResponse, methods=["GET"])
    app.add_api_route("/error", error, response_class=PlainTextResponse, methods=["GET"])
    return app
