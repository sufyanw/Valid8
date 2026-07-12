from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Literal

from app.schemas import JobStatusResponse, RecommendationResult


JobState = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class Job:
    job_id: str
    status: JobState
    created_at: float
    updated_at: float
    result: RecommendationResult | None = None
    error: str | None = None


class JobStore:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> Job:
        now = time.time()
        job = Job(job_id=str(uuid.uuid4()), status="queued", created_at=now, updated_at=now)
        async with self._lock:
            self._purge_expired_locked(now)
            self._jobs[job.job_id] = job
        return job

    async def set_running(self, job_id: str) -> None:
        await self._update(job_id, status="running")

    async def set_succeeded(self, job_id: str, result: RecommendationResult) -> None:
        await self._update(job_id, status="succeeded", result=result, error=None)

    async def set_failed(self, job_id: str, error: str) -> None:
        await self._update(job_id, status="failed", error=error)

    async def get(self, job_id: str) -> JobStatusResponse:
        now = time.time()
        async with self._lock:
            self._purge_expired_locked(now)
            job = self._jobs.get(job_id)
            if job is None:
                return JobStatusResponse(job_id=job_id, status="not_found")

            if now - job.created_at > self.ttl_seconds:
                self._jobs.pop(job_id, None)
                return JobStatusResponse(job_id=job_id, status="expired")

            return JobStatusResponse(
                job_id=job.job_id,
                status=job.status,
                result=job.result,
                error=job.error,
            )

    async def _update(
        self,
        job_id: str,
        *,
        status: JobState,
        result: RecommendationResult | None = None,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.updated_at = time.time()
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if error is None and status == "succeeded":
                job.error = None

    def _purge_expired_locked(self, now: float) -> None:
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if now - job.created_at > self.ttl_seconds
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)

