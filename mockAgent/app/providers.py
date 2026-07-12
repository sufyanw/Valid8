from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.schemas import ProviderRecord


@lru_cache
def load_providers(path: str | None = None) -> tuple[ProviderRecord, ...]:
    providers_path = Path(path) if path else get_settings().providers_path
    with providers_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return tuple(ProviderRecord.model_validate(item) for item in data["providers"])


def provider_lookup() -> dict[str, ProviderRecord]:
    return {provider.id: provider for provider in load_providers()}


def providers_for_prompt() -> list[dict]:
    return [provider.llm_view() for provider in load_providers()]

