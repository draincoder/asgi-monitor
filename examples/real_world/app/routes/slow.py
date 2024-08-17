import asyncio
import logging
import random

from fastapi import APIRouter, status
from opentelemetry import trace

from asgi_monitor.tracing import span

slow_router = APIRouter(
    prefix="/slow",
    tags=["Slow"],
    include_in_schema=True,
)
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@slow_router.get("/1000ms", status_code=status.HTTP_200_OK)
async def get_1000ms() -> dict:
    with tracer.start_as_current_span("sleep 0.1"):
        await asyncio.sleep(0.1)
        logger.error("sick")
    with tracer.start_as_current_span("sleep 0.2"):
        await asyncio.sleep(0.2)
        logger.error("still sick")
    with tracer.start_as_current_span("sleep 0.3"):
        await asyncio.sleep(0.3)
        logger.warning("normal")
    with tracer.start_as_current_span("sleep 0.4"):
        await asyncio.sleep(0.4)
        logger.info("full energy")
    return {"message": "ok", "status": "success"}


@span
def nested_func() -> int:
    num = random.randint(1, 10)  # noqa: S311
    current_span = trace.get_current_span()
    current_span.set_attribute("num", num)
    current_span.add_event("num rendered")
    return num


@slow_router.get("/span", status_code=status.HTTP_200_OK)
@span(name="span handler", attributes={"foo": "bar"})
async def get_span() -> dict:
    num = nested_func()
    return {"message": "ok", "status": "success", "num": num}
