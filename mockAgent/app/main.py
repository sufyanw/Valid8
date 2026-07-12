from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.jobs import JobStore
from app.locations import search_locations
from app.observability import add_request_logging, setup_observability
from app.providers import load_providers
from app.rate_limit import InMemoryRateLimiter
from app.recommendation import recommend
from app.schemas import JobCreateResponse, JobStatusResponse, RecommendationRequest


settings = get_settings()
setup_logger = logging.getLogger("accessible_travel_assistant")
job_store = JobStore(ttl_seconds=settings.job_ttl_seconds)
rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app = FastAPI(
    title="Accessible Travel Assistant",
    version="0.2.0",
    description="Stateless accessibility-aware travel provider recommendation API.",
)
setup_observability(app, settings)
add_request_logging(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def enforce_recommend_rate_limit(request: Request) -> None:
    await rate_limiter.check(request)


@app.get("/api/health")
async def health() -> dict:
    return {
        "ok": True,
        "provider_count": len(load_providers()),
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.get("/api/providers")
async def providers() -> dict:
    return {"providers": [provider.llm_view() for provider in load_providers()]}


@app.get("/api/locations")
async def locations(q: str = Query(default="", max_length=80)) -> dict:
    return {"locations": [location.model_dump() for location in search_locations(q)]}


@app.post(
    "/api/recommend",
    response_model=JobCreateResponse,
    dependencies=[Depends(enforce_recommend_rate_limit)],
)
async def create_recommendation(payload: RecommendationRequest) -> JobCreateResponse:
    job = await job_store.create()
    setup_logger.info(
        "recommendation_job_created",
        extra={
            "job_id": job.job_id,
            "quick_tag_count": len(payload.quick_tags),
            "transport_modes": ",".join(payload.transport_modes) or "not_sure",
            "duration_days": payload.duration_days,
            "origin_code": payload.origin.code if payload.origin else None,
            "destination_code": payload.destination.code if payload.destination else None,
        },
    )
    asyncio.create_task(_run_recommendation_job(job.job_id, payload))
    return JobCreateResponse(job_id=job.job_id, status="queued")


@app.get("/api/recommend/{job_id}", response_model=JobStatusResponse)
async def get_recommendation(job_id: str) -> JobStatusResponse:
    return await job_store.get(job_id)


async def _run_recommendation_job(job_id: str, payload: RecommendationRequest) -> None:
    await job_store.set_running(job_id)
    setup_logger.info("recommendation_job_started", extra={"job_id": job_id})
    try:
        result = await recommend(payload)
    except Exception as exc:  # noqa: BLE001 - user-facing failure state is intentional here.
        setup_logger.exception(
            "recommendation_job_failed",
            extra={"job_id": job_id, "error_type": type(exc).__name__},
        )
        await job_store.set_failed(job_id, _friendly_error(exc))
        return
    setup_logger.info(
        "recommendation_job_succeeded",
        extra={
            "job_id": job_id,
            "result_status": result.status,
            "provider_count": len(result.providers),
        },
    )
    await job_store.set_succeeded(job_id, result)


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    if "GEMINI_API_KEY" in message:
        return "The recommendation service is not configured yet. Set GEMINI_API_KEY and retry."
    if "Gemini API returned" in message:
        return "The recommendation service failed or timed out. Please retry."
    if "LLM response" in message or "unknown provider ID" in message:
        return "The recommendation service returned an invalid response. Please retry."
    return "The recommendation request failed. Please retry."


def _mount_frontend(static_app: FastAPI) -> None:
    dist_dir = settings.frontend_dist_dir
    assets_dir = dist_dir / "assets"
    logos_dir = dist_dir / "logos"

    if assets_dir.exists():
        static_app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    if logos_dir.exists():
        static_app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")

    @static_app.get("/", include_in_schema=False, response_model=None)
    async def spa_root():
        index = dist_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse(
            {
                "message": "Frontend build not found. Run `npm --prefix frontend install` "
                "and `npm --prefix frontend run build`."
            }
        )

    @static_app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        possible_file = dist_dir / full_path
        if possible_file.exists() and possible_file.is_file():
            return FileResponse(possible_file)

        index = dist_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend build not found."}, status_code=404)


_mount_frontend(app)
