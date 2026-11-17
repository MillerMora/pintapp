from fastapi import APIRouter, Response

from backend.controller.deps import ERR, SESSION_ERRORS, ContainerDep, CurrentSession
from backend.controller.schemas import FittingAddIn, FittingItemOut, FittingListOut

router = APIRouter(
    prefix="/api/v1/sessions/me/fitting",
    tags=["Probador"],
    responses=SESSION_ERRORS,
)


@router.get("", response_model=FittingListOut)
async def list_fitting(session: CurrentSession, container: ContainerDep):
    return FittingListOut(items=[FittingItemOut.from_domain(i) for i in container.fitting.items(session)])


@router.post(
    "",
    response_model=FittingItemOut,
    status_code=201,
    responses={404: ERR, 409: ERR, 422: ERR},
)
async def add_to_fitting(body: FittingAddIn, session: CurrentSession, container: ContainerDep):
    """Agrega una prenda al probador (solo si hay existencias). Una prenda por zona del cuerpo.

    Si la zona ya está ocupada responde 409 ``zone_occupied``; repite la petición con
    ``replace: true`` para cambiarla.
    """
    item = await container.fitting.add(
        session, body.garment_id, sku=body.sku, replace=body.replace
    )
    return FittingItemOut.from_domain(item)


@router.delete("/{garment_id}", status_code=204, responses={404: ERR})
async def remove_from_fitting(garment_id: str, session: CurrentSession, container: ContainerDep):
    await container.fitting.remove(session, garment_id)
    return Response(status_code=204)
