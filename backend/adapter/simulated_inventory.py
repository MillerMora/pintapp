"""Inventario simulado: lee un JSON local (``data/catalog_seed.json``).

Sirve para el prototipo. Para conectar el inventario real, implementa
``InventoryRepository`` (ver README) y selecciónalo en ``container.py``.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from backend.model.catalog import Category, Garment, Variant
from backend.model.text import normalize_text
from backend.port.inventory import GarmentFilter, GarmentPage, InventoryRepository

_HEX = r"^#[0-9A-Fa-f]{6}$"


class _SeedVariant(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    size: str = Field(min_length=1, max_length=16)
    in_stock: bool


class _SeedGarment(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=64)
    color: str = Field(min_length=1, max_length=32)
    color_hex: str = Field(pattern=_HEX)
    image_url: str | None = None
    variants: list[_SeedVariant] = Field(min_length=1)


class _Seed(BaseModel):
    garments: list[_SeedGarment]

    @model_validator(mode="after")
    def _unique_keys(self) -> "_Seed":
        ids = [g.id for g in self.garments]
        skus = [v.sku for g in self.garments for v in g.variants]
        if len(ids) != len(set(ids)):
            raise ValueError("El catálogo de prueba tiene ids de prenda repetidos")
        if len(skus) != len(set(skus)):
            raise ValueError("El catálogo de prueba tiene SKUs repetidos")
        return self


def _load_seed(path: Path) -> list[Garment]:
    seed = _Seed.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return [
        Garment(
            id=g.id,
            name=g.name,
            category=g.category,
            color=g.color,
            color_hex=g.color_hex,
            image_url=g.image_url,
            variants=tuple(Variant(v.sku, v.size, v.in_stock) for v in g.variants),
        )
        for g in seed.garments
    ]


def _matches(garment: Garment, flt: GarmentFilter) -> bool:
    if flt.category and normalize_text(garment.category) != normalize_text(flt.category):
        return False
    if flt.color and normalize_text(garment.color) != normalize_text(flt.color):
        return False
    if flt.size:
        wanted = normalize_text(flt.size)
        sized = [v for v in garment.variants if normalize_text(v.size) == wanted]
        if not sized:
            return False
        return any(v.in_stock for v in sized) if flt.in_stock_only else True
    return garment.in_stock if flt.in_stock_only else True


class SimulatedInventory(InventoryRepository):
    def __init__(self, seed_path: Path) -> None:
        self._garments = _load_seed(seed_path)
        self._by_id = {g.id: g for g in self._garments}

    async def list_categories(self) -> list[Category]:
        counts: dict[str, int] = {}
        for garment in self._garments:  # conserva el orden de aparición
            counts[garment.category] = counts.get(garment.category, 0) + 1
        return [Category(name, count) for name, count in counts.items()]

    async def list_garments(self, flt: GarmentFilter, *, limit: int, offset: int) -> GarmentPage:
        matching = [g for g in self._garments if _matches(g, flt)]
        return GarmentPage(items=tuple(matching[offset : offset + limit]), total=len(matching))

    async def get_garment(self, garment_id: str) -> Garment | None:
        return self._by_id.get(garment_id)
