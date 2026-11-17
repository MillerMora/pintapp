"""Puerto de inventario: lo que PintApp necesita saber del catálogo y las existencias.

PintApp NO administra inventario: lo consulta. Cualquier fuente (el e-commerce de la
tienda, su base de datos, una API) se conecta implementando esta interfaz. Es de solo
lectura a propósito.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.model.catalog import Category, Garment


@dataclass(frozen=True, slots=True)
class GarmentFilter:
    category: str | None = None
    size: str | None = None
    color: str | None = None
    in_stock_only: bool = False


@dataclass(frozen=True, slots=True)
class GarmentPage:
    items: tuple[Garment, ...]
    total: int


class InventoryRepository(ABC):
    @abstractmethod
    async def list_categories(self) -> list[Category]: ...

    @abstractmethod
    async def list_garments(
        self, flt: GarmentFilter, *, limit: int, offset: int
    ) -> GarmentPage: ...

    @abstractmethod
    async def get_garment(self, garment_id: str) -> Garment | None: ...
