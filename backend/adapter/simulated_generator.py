"""Generador de imágenes SIMULADO.

No usa IA: espera unos segundos (como lo haría una IA real), puede fallar a propósito
y devuelve la foto del cliente con rectángulos de color de cada prenda sobre su zona
del cuerpo y una franja que dice "SIMULACION". Sirve para probar todo el flujo
(cola, progreso, fallos, reintentos) antes de elegir un proveedor real.
"""

import asyncio
import io
import random

from PIL import Image, ImageColor, ImageDraw, ImageFont

from backend.model.enums import BodyZone
from backend.model.errors import GenerationFailedError
from backend.model.generation import GeneratedImage, GenerationInput
from backend.port.image_generator import ImageGenerator

# Cajas aproximadas (x0, y0, x1, y1) como fracción del ancho y alto de la foto.
_ZONE_BOXES: dict[BodyZone, tuple[float, float, float, float]] = {
    BodyZone.HEAD: (0.38, 0.02, 0.62, 0.13),
    BodyZone.UPPER_INNER: (0.28, 0.18, 0.72, 0.50),
    BodyZone.UPPER_OUTER: (0.24, 0.17, 0.76, 0.55),
    BodyZone.LOWER: (0.32, 0.50, 0.68, 0.84),
    BodyZone.FEET: (0.30, 0.85, 0.70, 0.91),
}


class SimulatedImageGenerator(ImageGenerator):
    def __init__(
        self,
        *,
        min_seconds: float,
        max_seconds: float,
        failure_rate: float,
        rng: random.Random | None = None,
    ) -> None:
        self._min = min_seconds
        self._max = max_seconds
        self._failure_rate = failure_rate
        self._rng = rng or random.Random()  # noqa: S311 - simulación, no es seguridad

    async def generate(self, data: GenerationInput) -> GeneratedImage:
        await asyncio.sleep(self._rng.uniform(self._min, self._max))
        if self._rng.random() < self._failure_rate:
            raise GenerationFailedError("Fallo simulado de la IA.")
        image = await asyncio.to_thread(self._render, data)
        return GeneratedImage(data=image, media_type="image/jpeg")

    @staticmethod
    def _render(data: GenerationInput) -> bytes:
        with Image.open(io.BytesIO(data.photo.data)) as photo:
            base = photo.convert("RGBA")
        width, height = base.size

        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for item in data.items:  # ya vienen ordenados por capa
            x0, y0, x1, y1 = _ZONE_BOXES[item.zone]
            red, green, blue = ImageColor.getrgb(item.garment.color_hex)[:3]
            draw.rounded_rectangle(
                (x0 * width, y0 * height, x1 * width, y1 * height),
                radius=max(6, width // 40),
                fill=(red, green, blue, 150),
                outline=(255, 255, 255, 210),
                width=max(2, width // 300),
            )
        composed = Image.alpha_composite(base, overlay)

        font = ImageFont.load_default(size=max(12, width // 30))
        label = "SIMULACION - " + ", ".join(i.garment.name for i in data.items)
        bar_height = max(28, height // 18)
        bar = Image.new("RGBA", (width, bar_height), (0, 0, 0, 170))
        ImageDraw.Draw(bar).text((10, bar_height // 4), label, fill=(255, 255, 255, 255), font=font)
        composed.alpha_composite(bar, dest=(0, height - bar_height))

        out = io.BytesIO()
        composed.convert("RGB").save(out, format="JPEG", quality=90)
        return out.getvalue()
