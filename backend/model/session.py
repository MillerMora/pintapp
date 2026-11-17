from dataclasses import dataclass, field

from backend.model.catalog import Garment, Variant
from backend.model.enums import BodyZone


@dataclass(frozen=True, slots=True)
class ProcessedPhoto:
    """Foto ya validada, sin metadatos, orientada y comprimida (siempre JPEG)."""

    data: bytes
    width: int
    height: int
    media_type: str = "image/jpeg"


@dataclass(frozen=True, slots=True)
class FittingItem:
    """Prenda elegida para el probador, con la zona del cuerpo que ocupa."""

    garment: Garment
    zone: BodyZone
    variant: Variant | None = None


@dataclass(slots=True)
class ClientSession:
    """Sesión temporal del cliente en el kiosco. Vive solo en memoria."""

    id: str  # identificador interno (para logs); NO es la credencial
    token: str  # credencial secreta que viaja en el encabezado X-Session-Token
    created_at: float  # reloj monotónico
    last_seen: float
    consent_accepted: bool = False
    photo: ProcessedPhoto | None = None
    fitting: dict[BodyZone, FittingItem] = field(default_factory=dict)
