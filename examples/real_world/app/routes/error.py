import logging

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

error_router = APIRouter(
    prefix="/error",
    tags=["Error"],
    include_in_schema=True,
)
logger = logging.getLogger(__name__)


@error_router.get("/500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def get_500_error() -> None:
    logger.error("Internal Server Error Occurred", extra={"status_code": 500})
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@error_router.get("/404", status_code=status.HTTP_404_NOT_FOUND)
async def get_404() -> None:
    logger.error("Not Found", extra={"status_code": 404})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


@error_router.get("/infinity", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def get_infinity() -> float:
    return 1 / 0
