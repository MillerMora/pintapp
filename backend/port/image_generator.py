"""Puerto del generador de imágenes (la IA que "viste" a la persona)."""

from abc import ABC, abstractmethod

from backend.model.generation import GeneratedImage, GenerationInput


class ImageGenerator(ABC):
    @abstractmethod
    async def generate(self, data: GenerationInput) -> GeneratedImage:
        """Devuelve la foto del cliente con las prendas puestas.

        Debe lanzar ``GenerationFailedError`` si no puede producir la imagen. El tiempo
        máximo lo controla el servicio de generación, no el adaptador.
        """
