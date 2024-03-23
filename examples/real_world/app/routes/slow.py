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
