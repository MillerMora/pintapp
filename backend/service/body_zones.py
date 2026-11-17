"""Traduce la categoría de una prenda a la zona del cuerpo donde se dibuja."""

from collections.abc import Mapping

from backend.model.enums import BodyZone
from backend.model.errors import UnsupportedCategoryError
from backend.model.text import normalize_text

# Orden en que se "visten" las capas: de abajo hacia arriba.
RENDER_ORDER: tuple[BodyZone, ...] = (
    BodyZone.LOWER,
    BodyZone.FEET,
    BodyZone.UPPER_INNER,
    BodyZone.UPPER_OUTER,
    BodyZone.HEAD,
)

_DEFAULT_CATEGORIES: dict[BodyZone, tuple[str, ...]] = {
    BodyZone.UPPER_INNER: (
        "camisa", "camisas", "camiseta", "camisetas", "buzo", "buzos", "sudadera", "sudaderas",
    ),
    BodyZone.UPPER_OUTER: ("chaqueta", "chaquetas", "abrigo", "abrigos"),
    BodyZone.LOWER: (
        "pantalon", "pantalones", "jean", "jeans", "short", "shorts", "falda", "faldas",
    ),
    BodyZone.FEET: (
        "zapato", "zapatos", "tenis", "bota", "botas", "sandalia", "sandalias",
    ),
    BodyZone.HEAD: ("gorra", "gorras", "sombrero", "sombreros"),
}


class BodyZoneResolver:
    """Mapa categoría -> zona. Se puede reemplazar con las categorías del e-commerce real."""

    def __init__(self, mapping: Mapping[BodyZone, tuple[str, ...]] | None = None) -> None:
        source = mapping or _DEFAULT_CATEGORIES
        self._by_category = {
            normalize_text(name): zone for zone, names in source.items() for name in names
        }

    def resolve(self, category: str) -> BodyZone:
        zone = self._by_category.get(normalize_text(category))
        if zone is None:
            raise UnsupportedCategoryError(category=category)
        return zone
