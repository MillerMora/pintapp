"""Almacenes en memoria para sesiones y trabajos (un solo proceso)."""

from backend.model.enums import GenerationStatus
from backend.model.generation import GenerationJob
from backend.model.session import ClientSession
from backend.port.stores import JobStore, SessionStore


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._by_token: dict[str, ClientSession] = {}

    async def add(self, session: ClientSession) -> None:
        self._by_token[session.token] = session

    async def get(self, token: str) -> ClientSession | None:
        return self._by_token.get(token)

    async def save(self, session: ClientSession) -> None:
        # Los objetos se comparten por referencia: no hay nada que persistir.
        self._by_token[session.token] = session

    async def delete(self, token: str) -> ClientSession | None:
        return self._by_token.pop(token, None)

    async def count(self) -> int:
        return len(self._by_token)

    async def pop_expired(
        self, *, now: float, idle_ttl: float, max_lifetime: float
    ) -> list[ClientSession]:
        expired = [
            s
            for s in self._by_token.values()
            if now - s.last_seen > idle_ttl or now - s.created_at > max_lifetime
        ]
        for session in expired:
            del self._by_token[session.token]
        return expired


class InMemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}

    async def add(self, job: GenerationJob) -> None:
        self._jobs[job.id] = job

    async def get(self, job_id: str) -> GenerationJob | None:
        return self._jobs.get(job_id)

    async def save(self, job: GenerationJob) -> None:
        self._jobs[job.id] = job

    async def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    async def list_by_session(self, session_id: str) -> list[GenerationJob]:
        jobs = [j for j in self._jobs.values() if j.session_id == session_id]
        return sorted(jobs, key=lambda j: j.sequence)

    async def delete_by_session(self, session_id: str) -> list[GenerationJob]:
        removed = [j for j in self._jobs.values() if j.session_id == session_id]
        for job in removed:
            del self._jobs[job.id]
        return removed

    async def count_queued_before(self, sequence: int) -> int:
        return sum(
            1
            for j in self._jobs.values()
            if j.status is GenerationStatus.QUEUED and j.sequence < sequence
        )
