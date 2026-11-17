"""Ensamblado de la aplicación: aquí se decide qué implementación usa cada puerto.

Para cambiar el inventario simulado por el real, o la IA simulada por una real,
solo hay que tocar ``_build_inventory`` / ``_build_generator`` (ver README).
"""

import asyncio
import contextlib
import logging

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.adapter.database import create_engine
from backend.adapter.memory_stores import InMemoryJobStore, InMemorySessionStore
from backend.adapter.simulated_generator import SimulatedImageGenerator
from backend.adapter.simulated_inventory import SimulatedInventory
from backend.config import Settings
from backend.port.image_generator import ImageGenerator
from backend.port.inventory import InventoryRepository
from backend.service.body_zones import BodyZoneResolver
from backend.service.catalog_service import CatalogService
from backend.service.fitting_service import FittingService
from backend.service.generation_service import GenerationService
from backend.service.photo import PhotoRules, PhotoService
from backend.service.session_service import SessionService

logger = logging.getLogger(__name__)


def _build_inventory(settings: Settings) -> InventoryRepository:
    match settings.inventory_provider:
        case "simulated":
            return SimulatedInventory(settings.catalog_seed_path)


def _build_generator(settings: Settings) -> ImageGenerator:
    match settings.generator_provider:
        case "simulated":
            return SimulatedImageGenerator(
                min_seconds=settings.sim_min_seconds,
                max_seconds=settings.sim_max_seconds,
                failure_rate=settings.sim_failure_rate,
            )


class Container:
    def __init__(
        self,
        settings: Settings,
        *,
        inventory: InventoryRepository | None = None,
        generator: ImageGenerator | None = None,
    ) -> None:
        self.settings = settings
        self.db_engine: AsyncEngine | None = (
            create_engine(settings.database_url) if settings.database_url else None
        )

        session_store = InMemorySessionStore()
        inventory = inventory or _build_inventory(settings)

        self.generation = GenerationService(
            jobs=InMemoryJobStore(),
            generator=generator or _build_generator(settings),
            workers=settings.generation_workers,
            queue_max=settings.generation_queue_max,
            timeout_seconds=settings.generation_timeout_seconds,
            max_retries=settings.generation_max_retries,
        )
        self.sessions = SessionService(
            session_store,
            idle_ttl_seconds=settings.session_idle_ttl_seconds,
            max_lifetime_seconds=settings.session_max_lifetime_seconds,
            max_active=settings.session_max_active,
            on_close=[self.generation.purge_session],
        )
        self.catalog = CatalogService(inventory)
        self.fitting = FittingService(inventory, BodyZoneResolver(), session_store)
        self.photos = PhotoService(
            PhotoRules(
                max_pixels=settings.photo_max_pixels,
                min_side_px=settings.photo_min_side_px,
                max_side_px=settings.photo_max_side_px,
                jpeg_quality=settings.photo_jpeg_quality,
            )
        )
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.generation.start()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(), name="session-cleanup")

    async def stop(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
        await self.generation.stop()
        if self.db_engine is not None:
            await self.db_engine.dispose()

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.session_cleanup_interval_seconds)
            try:
                await self.sessions.purge_expired()
            except Exception:
                logger.exception("Falló la limpieza de sesiones expiradas")
