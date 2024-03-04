from fastapi import APIRouter, status

healthcheck_router = APIRouter(
    prefix="/healthcheck",
    tags=["Healthcheck"],
    include_in_schema=True,
)


@healthcheck_router.get("/", status_code=status.HTTP_200_OK)
async def get_status() -> dict:
    return {"message": "ok", "status": "success"}
