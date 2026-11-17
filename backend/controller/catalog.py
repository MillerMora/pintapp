from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.controller.deps import ERR, SESSION_ERRORS, ContainerDep, current_session
from backend.controller.schemas import CategoryOut, GarmentListOut, GarmentOut
from backend.port.inventory import GarmentFilter

router = APIRouter(
    prefix="/api/v1/catalog",
    tags=["Catálogo"],
    dependencies=[Depends(current_session)],
    responses=SESSION_ERRORS,
)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(container: ContainerDep):
    return [CategoryOut.from_domain(c) for c in await container.catalog.categories()]


@router.get("/garments", response_model=GarmentListOut)
async def list_garments(
    container: ContainerDep,
    category: Annotated[str | None, Query(max_length=64)] = None,
    size: Annotated[str | None, Query(max_length=16)] = None,
    color: Annotated[str | None, Query(max_length=32)] = None,
    in_stock: Annotated[bool, Query(description="Solo prendas con existencias")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Prendas del catálogo; filtra por categoría, talla o color (sin distinguir tildes)."""
    page = await container.catalog.garments(
        GarmentFilter(category=category, size=size, color=color, in_stock_only=in_stock),
        limit=limit,
        offset=offset,
    )
    return GarmentListOut(
        items=[GarmentOut.from_domain(g) for g in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.get("/garments/{garment_id}", response_model=GarmentOut, responses={404: ERR})
async def get_garment(garment_id: str, container: ContainerDep):
    return GarmentOut.from_domain(await container.catalog.garment(garment_id))
