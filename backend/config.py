"""Configuración del backend.

Los valores se leen de variables de entorno con prefijo ``PINTAPP_`` o del archivo
``backend/.env`` (ver ``.env.example``). Los valores por defecto sirven para
desarrollo local.
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

# Texto provisional: debe ser reemplazado por el texto legal definitivo de la tienda.
DEFAULT_TERMS_TEXT = (
    "Al continuar aceptas que PintApp use tu fotografía únicamente para generar "
    "una vista previa de las prendas que elijas. La foto se procesa de forma "
    "temporal, no se guarda de manera permanente y se elimina cuando termina tu "
    "sesión. Si no aceptas, la sesión se cierra sin guardar nada."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PINTAPP_",
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Servidor ---
    environment: Literal["development", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = Field(default_factory=list)

    # --- Proveedores intercambiables (puntos de extensión) ---
    inventory_provider: Literal["simulated"] = "simulated"
    generator_provider: Literal["simulated"] = "simulated"
    database_url: str | None = None
    catalog_seed_path: Path = BASE_DIR / "data" / "catalog_seed.json"

    # --- Sesión del cliente (kiosco) ---
    session_idle_ttl_seconds: int = Field(default=600, ge=1)
    session_max_lifetime_seconds: int = Field(default=1800, ge=1)
    session_max_active: int = Field(default=50, ge=1)
    session_cleanup_interval_seconds: float = Field(default=30.0, gt=0)
    terms_version: str = "1.0"
    terms_text: str = DEFAULT_TERMS_TEXT

    # --- Foto ---
    photo_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1024)
    photo_max_pixels: int = Field(default=40_000_000, ge=10_000)
    photo_min_side_px: int = Field(default=480, ge=1)
    photo_max_side_px: int = Field(default=1536, ge=64)
    photo_jpeg_quality: int = Field(default=88, ge=40, le=100)

    # --- Generación de imágenes ---
    generation_workers: int = Field(default=1, ge=1, le=16)
    generation_queue_max: int = Field(default=20, ge=1)
    generation_timeout_seconds: float = Field(default=60.0, gt=0)
    generation_max_retries: int = Field(default=3, ge=0, le=10)

    # --- Generador simulado ---
    sim_min_seconds: float = Field(default=3.0, ge=0)
    sim_max_seconds: float = Field(default=6.0, ge=0)
    sim_failure_rate: float = Field(default=0.0, ge=0, le=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.sim_max_seconds < self.sim_min_seconds:
            raise ValueError("sim_max_seconds no puede ser menor que sim_min_seconds")
        if self.photo_min_side_px > self.photo_max_side_px:
            raise ValueError("photo_min_side_px no puede superar photo_max_side_px")
        if self.session_max_lifetime_seconds < self.session_idle_ttl_seconds:
            raise ValueError(
                "session_max_lifetime_seconds no puede ser menor que session_idle_ttl_seconds"
            )
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.environment == "development"
