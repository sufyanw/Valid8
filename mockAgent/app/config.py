from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    gemini_api_base_url: str
    gemini_timeout_seconds: float
    job_ttl_seconds: int
    rate_limit_max_requests: int
    rate_limit_window_seconds: int
    allow_fake_llm: bool
    providers_path: Path
    frontend_dist_dir: Path
    cors_origins: tuple[str, ...]
    log_level: str
    otel_enabled: bool
    otel_service_name: str
    otel_environment: str
    otel_exporter_otlp_endpoint: str | None
    otel_exporter_otlp_headers: str | None


@lru_cache
def get_settings() -> Settings:
    cors_raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        gemini_api_base_url=os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com",
        ).rstrip("/"),
        gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45")),
        job_ttl_seconds=int(os.getenv("JOB_TTL_SECONDS", "600")),
        rate_limit_max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10")),
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")),
        allow_fake_llm=_as_bool(os.getenv("ALLOW_FAKE_LLM"), default=False),
        providers_path=Path(
            os.getenv("PROVIDERS_PATH", str(PROJECT_ROOT / "app" / "data" / "providers.json"))
        ),
        frontend_dist_dir=Path(
            os.getenv("FRONTEND_DIST_DIR", str(PROJECT_ROOT / "frontend" / "dist"))
        ),
        cors_origins=tuple(origin.strip() for origin in cors_raw.split(",") if origin.strip()),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        otel_enabled=_as_bool(os.getenv("OTEL_ENABLED"), default=True),
        otel_service_name=os.getenv("OTEL_SERVICE_NAME", "accessible-travel-assistant"),
        otel_environment=os.getenv("OTEL_ENVIRONMENT", os.getenv("HEROKU_APP_NAME", "local")),
        otel_exporter_otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        otel_exporter_otlp_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
    )
