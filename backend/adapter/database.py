"""Conexión a la base de datos relacional, independiente del motor.

SQLAlchemy traduce al dialecto de cada motor, así que el mismo código sirve para
PostgreSQL, MariaDB/MySQL (y SQLite en desarrollo). Solo cambia la URL y el driver:

    postgresql+psycopg://usuario:clave@host:5432/base      (uv sync --extra postgres)
    mariadb+asyncmy://usuario:clave@host:3306/base         (uv sync --extra mariadb)

En el prototipo todavía no se usa para nada más que verificar la conexión: el
inventario es simulado. Cuando exista la BD real se implementa un
``InventoryRepository`` que use este motor (ver README).
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    try:
        return create_async_engine(database_url, pool_pre_ping=True)
    except Exception as exc:  # URL mal escrita, dialecto desconocido o driver sin instalar
        # No se incluye la URL en el mensaje para no filtrar la contraseña a los logs.
        raise RuntimeError(
            "PINTAPP_DATABASE_URL no es válida o falta el driver de la base de datos "
            "(ver .env.example y README)."
        ) from exc


async def check_connection(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("No hay conexión con la base de datos", exc_info=True)
        return False
    return True
