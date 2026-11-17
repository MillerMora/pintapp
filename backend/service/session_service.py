"""Ciclo de vida de la sesión temporal del cliente en el kiosco."""

import logging
import secrets
import time
from collections.abc import Awaitable, Callable, Sequence

from backend.model.errors import (
    ConsentRequiredError,
    SessionExpiredError,
    SessionRequiredError,
    TooManySessionsError,
)
from backend.model.session import ClientSession, ProcessedPhoto
from backend.port.stores import SessionStore

logger = logging.getLogger(__name__)

CloseHook = Callable[[ClientSession], Awaitable[None]]


class SessionService:
    def __init__(
        self,
        store: SessionStore,
        *,
        idle_ttl_seconds: float,
        max_lifetime_seconds: float,
        max_active: int,
        on_close: Sequence[CloseHook] = (),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._store = store
        self._idle_ttl = idle_ttl_seconds
        self._max_lifetime = max_lifetime_seconds
        self._max_active = max_active
        self._on_close = tuple(on_close)
        self._clock = clock

    async def create(self) -> ClientSession:
        if await self._store.count() >= self._max_active:
            await self.purge_expired()
            if await self._store.count() >= self._max_active:
                raise TooManySessionsError()
        now = self._clock()
        session = ClientSession(
            id=secrets.token_hex(4),
            token=secrets.token_urlsafe(32),
            created_at=now,
            last_seen=now,
        )
        await self._store.add(session)
        logger.info("Sesión %s creada", session.id)
        return session

    async def authenticate(self, token: str | None) -> ClientSession:
        if not token:
            raise SessionRequiredError()
        session = await self._store.get(token)
        if session is None:
            raise SessionExpiredError()
        now = self._clock()
        if self._is_expired(session, now):
            await self.close(session)
            raise SessionExpiredError()
        session.last_seen = now
        await self._store.save(session)
        return session

    def remaining_seconds(self, session: ClientSession) -> int:
        now = self._clock()
        idle_left = self._idle_ttl - (now - session.last_seen)
        life_left = self._max_lifetime - (now - session.created_at)
        return max(0, int(min(idle_left, life_left)))

    async def accept_consent(self, session: ClientSession) -> None:
        session.consent_accepted = True
        await self._store.save(session)

    def require_consent(self, session: ClientSession) -> None:
        if not session.consent_accepted:
            raise ConsentRequiredError()

    async def set_photo(self, session: ClientSession, photo: ProcessedPhoto) -> None:
        self.require_consent(session)
        session.photo = photo
        await self._store.save(session)

    async def close(self, session: ClientSession) -> None:
        """Borra la sesión y todo lo asociado (foto, prendas, imágenes generadas)."""
        await self._store.delete(session.token)
        await self._run_hooks(session)
        logger.info("Sesión %s cerrada", session.id)

    async def purge_expired(self) -> int:
        expired = await self._store.pop_expired(
            now=self._clock(), idle_ttl=self._idle_ttl, max_lifetime=self._max_lifetime
        )
        for session in expired:
            await self._run_hooks(session)
        if expired:
            logger.info("%d sesión(es) expirada(s) eliminada(s)", len(expired))
        return len(expired)

    def _is_expired(self, session: ClientSession, now: float) -> bool:
        return (
            now - session.last_seen > self._idle_ttl
            or now - session.created_at > self._max_lifetime
        )

    async def _run_hooks(self, session: ClientSession) -> None:
        for hook in self._on_close:
            try:
                await hook(session)
            except Exception:
                logger.exception("Falló una limpieza al cerrar la sesión %s", session.id)
