from backend.model.catalog import Category, Garment
from backend.model.errors import GarmentNotFoundError
from backend.port.inventory import GarmentFilter, GarmentPage, InventoryRepository


class CatalogService:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._inventory = inventory

    async def categories(self) -> list[Category]:
        return await self._inventory.list_categories()

    async def garments(self, flt: GarmentFilter, *, limit: int, offset: int) -> GarmentPage:
        return await self._inventory.list_garments(flt, limit=limit, offset=offset)

    async def garment(self, garment_id: str) -> Garment:
        garment = await self._inventory.get_garment(garment_id)
        if garment is None:
            raise GarmentNotFoundError(garment_id=garment_id)
        return garment
