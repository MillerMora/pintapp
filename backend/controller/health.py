from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend import __version__
from backend.adapter.database import check_connection
from backend.controller.deps import ContainerDep
from backend.controller.schemas import HealthOut

router = APIRouter(tags=["Sistema"])


@router.get("/health", response_model=HealthOut, responses={503: {"model": HealthOut}})
async def health(container: ContainerDep):
    database = "not_configured"
    if container.db_engine is not None:
        database = "ok" if await check_connection(container.db_engine) else "unavailable"
    healthy = database != "unavailable"
    payload = HealthOut(status="ok" if healthy else "degraded", version=__version__, database=database)
    return payload if healthy else JSONResponse(status_code=503, content=payload.model_dump())
