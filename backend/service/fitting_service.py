"""Lista de prendas del probador de una sesión (una prenda por zona del cuerpo)."""

from backend.model.errors import (
    FittingItemNotFoundError,
    GarmentNotFoundError,
    GarmentOutOfStockError,
    VariantNotFoundError,
    ZoneOccupiedError,
)
from backend.model.session import ClientSession, FittingItem
from backend.port.inventory import InventoryRepository
from backend.port.stores import SessionStore
from backend.service.body_zones import RENDER_ORDER, BodyZoneResolver


class FittingService:
    def __init__(
        self,
        inventory: InventoryRepository,
        resolver: BodyZoneResolver,
        store: SessionStore,
    ) -> None:
        self._inventory = inventory
        self._resolver = resolver
        self._store = store

    async def add(
        self,
        session: ClientSession,
        garment_id: str,
        *,
        sku: str | None = None,
        replace: bool = False,
    ) -> FittingItem:
        garment = await self._inventory.get_garment(garment_id)
        if garment is None:
            raise GarmentNotFoundError(garment_id=garment_id)
        zone = self._resolver.resolve(garment.category)

        variant = None
        if sku is not None:
            variant = garment.variant(sku)
            if variant is None:
                raise VariantNotFoundError(garment_id=garment_id, sku=sku)
            if not variant.in_stock:
                raise GarmentOutOfStockError(garment_id=garment_id, sku=sku)
        elif not garment.in_stock:
            raise GarmentOutOfStockError(garment_id=garment_id)

        current = session.fitting.get(zone)
        if current is not None and current.garment.id != garment.id and not replace:
            raise ZoneOccupiedError(
                zone=zone.value,
                occupied_by=current.garment.id,
                occupied_by_name=current.garment.name,
            )

        item = FittingItem(garment=garment, zone=zone, variant=variant)
        session.fitting[zone] = item
        await self._store.save(session)
        return item

    async def remove(self, session: ClientSession, garment_id: str) -> None:
        for zone, item in session.fitting.items():
            if item.garment.id == garment_id:
                del session.fitting[zone]
                await self._store.save(session)
                return
        raise FittingItemNotFoundError(garment_id=garment_id)

    @staticmethod
    def items(session: ClientSession) -> list[FittingItem]:
        return [session.fitting[zone] for zone in RENDER_ORDER if zone in session.fitting]
