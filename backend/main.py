"""Punto de entrada: levanta el servidor HTTP.

Desde la raíz del repositorio:  uv run --project backend python -m backend.main
"""

import uvicorn

from backend.config import BASE_DIR, Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "backend.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.reload,
        reload_dirs=[str(BASE_DIR)] if settings.reload else None,
        server_header=False,  # no anunciar el servidor en las respuestas
    )


if __name__ == "__main__":
    main()
