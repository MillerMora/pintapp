"""Validación y procesamiento de la foto del cliente.

La foto es entrada no confiable: se valida el formato real (no el que declara el
cliente), se limitan bytes y píxeles ANTES de decodificar, se corrige la orientación,
se eliminan metadatos (EXIF/GPS) y se recomprime a JPEG. El resultado es lo único que
se guarda en la sesión.
"""

import asyncio
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from backend.model.errors import InvalidPhotoError
from backend.model.session import ProcessedPhoto

_ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

_MESSAGES = {
    "empty": "La foto está vacía.",
    "unsupported_format": "El formato no es válido. Usa JPEG, PNG o WebP.",
    "too_many_pixels": "La foto tiene una resolución demasiado alta.",
    "too_small": "La foto es muy pequeña. Acércate a la cámara o mejora la resolución.",
    "animated": "No se aceptan imágenes animadas.",
    "unreadable": "No se pudo leer la foto: está dañada o incompleta.",
}


@dataclass(frozen=True, slots=True)
class PhotoRules:
    max_pixels: int
    min_side_px: int
    max_side_px: int
    jpeg_quality: int


def _reject(reason: str) -> InvalidPhotoError:
    return InvalidPhotoError(_MESSAGES[reason], reason=reason)


def process_photo(raw: bytes, rules: PhotoRules) -> ProcessedPhoto:
    """Función síncrona y pesada (CPU): llamar con ``asyncio.to_thread``."""
    if not raw:
        raise _reject("empty")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in _ALLOWED_FORMATS:
                raise _reject("unsupported_format")
            width, height = probe.size  # solo lee la cabecera: no decodifica los píxeles
            if width * height > rules.max_pixels:
                raise _reject("too_many_pixels")
            if min(width, height) < rules.min_side_px:
                raise _reject("too_small")
            if getattr(probe, "is_animated", False):
                raise _reject("animated")
            probe.verify()
        with Image.open(io.BytesIO(raw)) as decoded:
            decoded.load()
            oriented = ImageOps.exif_transpose(decoded)
            image = _flatten_to_rgb(oriented)
    except InvalidPhotoError:
        raise
    except UnidentifiedImageError as exc:  # no es una imagen reconocible
        raise _reject("unsupported_format") from exc
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        raise _reject("unreadable") from exc

    image.thumbnail((rules.max_side_px, rules.max_side_px), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=rules.jpeg_quality, optimize=True)  # sin EXIF
    return ProcessedPhoto(data=out.getvalue(), width=image.width, height=image.height)


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if not has_alpha:
        return image.convert("RGB")
    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


class PhotoService:
    def __init__(self, rules: PhotoRules) -> None:
        self._rules = rules

    async def process(self, raw: bytes) -> ProcessedPhoto:
        return await asyncio.to_thread(process_photo, raw, self._rules)
