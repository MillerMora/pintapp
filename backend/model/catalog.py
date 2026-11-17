from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Variant:
    """Una combinación vendible de una prenda (por ahora, una talla)."""

    sku: str
    size: str
    in_stock: bool


@dataclass(frozen=True, slots=True)
class Garment:
    id: str
    name: str
    category: str
    color: str
    color_hex: str
    variants: tuple[Variant, ...]
    # Imagen de referencia de la prenda; la usará un generador real. El simulado la ignora.
    image_url: str | None = None

    @property
    def in_stock(self) -> bool:
        return any(v.in_stock for v in self.variants)

    def variant(self, sku: str) -> Variant | None:
        return next((v for v in self.variants if v.sku == sku), None)


@dataclass(frozen=True, slots=True)
class Category:
    name: str
    garment_count: int
