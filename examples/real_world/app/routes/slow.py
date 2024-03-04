import asyncio
import logging

from fastapi import APIRouter, status
from opentelemetry import trace

slow_router = APIRouter(
    prefix="/slow",
    tags=["Slow"],
    include_in_schema=True,
)
logger = logging.getLogger(__name__)


@slow_router.get("/1000ms", status_code=status.HTTP_200_OK)
async def get_1000ms() -> dict:
    with trace.get_tracer("asgi-monitor").start_as_current_span("sleep 0.1"):
        await asyncio.sleep(0.1)
    with trace.get_tracer("asgi-monitor").start_as_current_span("sleep 0.2"):
        await asyncio.sleep(0.2)
    with trace.get_tracer("asgi-monitor").start_as_current_span("sleep 0.3"):
        await asyncio.sleep(0.3)
    with trace.get_tracer("asgi-monitor").start_as_current_span("sleep 0.4"):
        await asyncio.sleep(0.4)
    return {"message": "ok", "status": "success"}
