"""Puertos de almacenamiento temporal (sesiones y trabajos de generación).

Hoy viven en memoria; mañana podrían vivir en Redis sin tocar los servicios.
"""

from abc import ABC, abstractmethod

from backend.model.generation import GenerationJob
from backend.model.session import ClientSession


class SessionStore(ABC):
    @abstractmethod
    async def add(self, session: ClientSession) -> None: ...

    @abstractmethod
    async def get(self, token: str) -> ClientSession | None: ...

    @abstractmethod
    async def save(self, session: ClientSession) -> None: ...

    @abstractmethod
    async def delete(self, token: str) -> ClientSession | None: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def pop_expired(
        self, *, now: float, idle_ttl: float, max_lifetime: float
    ) -> list[ClientSession]:
        """Quita y devuelve las sesiones que superaron su inactividad o su vida máxima."""


class JobStore(ABC):
    @abstractmethod
    async def add(self, job: GenerationJob) -> None: ...

    @abstractmethod
    async def get(self, job_id: str) -> GenerationJob | None: ...

    @abstractmethod
    async def save(self, job: GenerationJob) -> None: ...

    @abstractmethod
    async def delete(self, job_id: str) -> None: ...

    @abstractmethod
    async def list_by_session(self, session_id: str) -> list[GenerationJob]: ...

    @abstractmethod
    async def delete_by_session(self, session_id: str) -> list[GenerationJob]: ...

    @abstractmethod
    async def count_queued_before(self, sequence: int) -> int: ...
