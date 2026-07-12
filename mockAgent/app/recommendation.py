from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from app.config import get_settings
from app.gemini import GeminiClient
from app.prompt import SYSTEM_INSTRUCTIONS, build_user_prompt
from app.providers import load_providers
from app.schemas import (
    DurationAnalysis,
    ProviderRecommendation,
    ProviderRecord,
    RecommendationRequest,
    RecommendationResult,
)


DISCLAIMER = (
    "Accommodation policies can change. Confirm accessibility details directly with "
    "the provider before booking."
)

_FEATURE_FLAGS_PATH = Path(__file__).resolve().parents[1] / "config" / "feature_flags.json"


def read_feature_flags() -> dict:
    try:
        with open(_FEATURE_FLAGS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"force_failure": False}


def write_feature_flags(flags: dict) -> dict:
    """Persists to the committed config file (not an env var) so flipping a
    flag produces a real, citable git diff for 4sight to reason over."""
    current = read_feature_flags()
    current.update(flags)
    with open(_FEATURE_FLAGS_PATH, "w") as f:
        json.dump(current, f, indent=2)
        f.write("\n")
    return current


def _force_failure_enabled() -> bool:
    """Demo/testing lever for 4sight: when true, every recommendation
    request fails deterministically."""
    return bool(read_feature_flags().get("force_failure", False))


async def recommend(payload: RecommendationRequest) -> RecommendationResult:
    if _force_failure_enabled():
        raise RuntimeError(
            "Simulated failure: force_failure is enabled in config/feature_flags.json"
        )

    settings = get_settings()
    providers = load_providers()

    if settings.allow_fake_llm:
        return build_local_recommendation(payload, providers)

    client = GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        base_url=settings.gemini_api_base_url,
        timeout_seconds=settings.gemini_timeout_seconds,
    )
    prompt = build_user_prompt(payload, [provider.llm_view() for provider in providers])
    raw_text = await client.generate_json(SYSTEM_INSTRUCTIONS, prompt)
    return parse_and_validate_llm_result(raw_text, providers)


def parse_and_validate_llm_result(
    raw_text: str,
    providers: Iterable[ProviderRecord],
) -> RecommendationResult:
    text = _extract_json(raw_text)
    try:
        result = RecommendationResult.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("LLM response was not valid recommendation JSON.") from exc

    return sanitize_result(result, providers)


def sanitize_result(
    result: RecommendationResult,
    providers: Iterable[ProviderRecord],
) -> RecommendationResult:
    provider_map = {provider.id: provider for provider in providers}
    clean_recommendations: list[ProviderRecommendation] = []

    seen: set[str] = set()
    for recommendation in result.providers:
        provider = provider_map.get(recommendation.provider_id)
        if provider is None:
            raise ValueError(f"LLM recommended unknown provider ID: {recommendation.provider_id}")
        if provider.id in seen:
            continue
        seen.add(provider.id)
        recommendation.provider_name = provider.name
        recommendation.mode = provider.mode
        recommendation.policy_url = provider.policy_url
        recommendation.booking_url = provider.booking_url
        recommendation.logo_url = provider.logo_url
        clean_recommendations.append(recommendation)

    result.providers = clean_recommendations[:3]
    result.disclaimer = DISCLAIMER

    if result.status == "ok" and not result.providers:
        raise ValueError("LLM returned status ok without any provider recommendations.")

    if result.status != "ok":
        result.providers = []

    return result


def _extract_json(raw_text: str) -> str:
    text = raw_text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return text[start : end + 1]


def build_local_recommendation(
    payload: RecommendationRequest,
    providers: Iterable[ProviderRecord],
) -> RecommendationResult:
    """Deterministic development fallback used only when ALLOW_FAKE_LLM=true."""

    text = " ".join(
        [
            payload.needs_description,
            payload.transport_preferences or "",
            payload.trip_duration,
            " ".join(payload.transport_modes),
            payload.origin.city if payload.origin else "",
            payload.origin.code if payload.origin else "",
            payload.destination.city if payload.destination else "",
            payload.destination.code if payload.destination else "",
            " ".join(payload.quick_tags),
        ]
    ).lower()
    detected = _detect_needs(text, payload.quick_tags)
    requested_modes = _detect_modes(text, payload.transport_modes)
    duration = _parse_duration(payload.trip_duration, payload.duration_days)

    if _looks_international(text):
        return RecommendationResult(
            status="unsupported_region",
            detected_needs=detected,
            requested_modes=requested_modes,
            recommended_mode="unsupported",
            duration=duration,
            summary="This v1 app only covers US travel providers.",
            providers=[],
            next_steps=["Use this app for US-only trips or verify international options directly."],
            disclaimer=DISCLAIMER,
        )

    if "rental" in text and ("blind" in text or "low vision" in text or "cannot drive" in text):
        return RecommendationResult(
            status="mode_conflict",
            detected_needs=detected,
            requested_modes=["unsupported"],
            recommended_mode="unsupported",
            duration=duration,
            summary="The requested mode appears to conflict with the stated need.",
            providers=[],
            next_steps=[
                "Consider rail, air, taxi, rideshare, or traveling with a licensed driver instead."
            ],
            disclaimer=DISCLAIMER,
        )

    scored: list[ProviderRecommendation] = []
    for provider in providers:
        if requested_modes and provider.mode not in requested_modes:
            continue
        score = _score_provider(provider, detected, duration.band)
        if score >= 45:
            scored.append(
                ProviderRecommendation(
                    provider_id=provider.id,
                    score=score,
                    why_recommended=[
                        provider.accommodation_summary,
                        f"Dataset categories match: {', '.join(set(detected) & set(provider.categories)) or 'general accessibility support'}.",
                    ],
                    watchouts=[
                        "Route or service-area availability is not checked in v1.",
                        provider.duration_relevant.duration_notes,
                    ],
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    if not scored:
        return RecommendationResult(
            status="no_strong_match",
            detected_needs=detected,
            requested_modes=requested_modes or ["not_sure"],
            recommended_mode="not_sure",
            duration=duration,
            summary="No strong provider match was found in the curated v1 dataset.",
            providers=[],
            next_steps=[
                "Broaden the transportation mode or contact a provider directly to confirm accommodations."
            ],
            disclaimer=DISCLAIMER,
        )

    result = RecommendationResult(
        status="ok",
        detected_needs=detected,
        requested_modes=requested_modes or ["not_sure"],
        recommended_mode=scored[0].mode or "not_sure",
        duration=duration,
        summary="These options best match the stated accessibility needs in the curated dataset.",
        providers=scored[:3],
        next_steps=[
            "Confirm the accommodation with the provider before booking.",
            "Add accessibility requests during booking or in the provider's manage-trip flow.",
        ],
        disclaimer=DISCLAIMER,
    )
    return sanitize_result(result, providers)


def _detect_needs(text: str, quick_tags: list[str]) -> list[str]:
    needs = set(quick_tags)
    checks = {
        "mobility": ["wheelchair", "scooter", "walker", "mobility", "cane", "transfer"],
        "vision": ["blind", "low vision", "vision", "visually impaired"],
        "hearing": ["deaf", "hearing", "hard of hearing", "caption"],
        "sensory": ["sensory", "autism", "overstimulated", "noise", "quiet"],
        "cognitive": ["cognitive", "developmental", "intellectual", "memory"],
        "service_animal": ["service animal", "guide dog", "service dog"],
        "medical": ["medical", "oxygen", "medication", "battery", "cpap", "ventilator"],
    }
    for need, keywords in checks.items():
        if any(keyword in text for keyword in keywords):
            needs.add(need)
    if not needs:
        needs.add("other")
    return sorted(needs)


def _detect_modes(text: str, selected_modes: list[str] | None = None) -> list[str]:
    if selected_modes:
        modes = [mode for mode in selected_modes if mode not in {"not_sure", "unsupported"}]
        if modes:
            return sorted(set(modes))

    modes: set[str] = set()
    if any(word in text for word in ["flight", "fly", "airline", "plane", "air"]):
        modes.add("air")
    if any(word in text for word in ["train", "rail", "amtrak"]):
        modes.add("rail")
    if any(word in text for word in ["uber", "lyft", "rideshare", "ride share", "ride-hail"]):
        modes.add("rideshare")
    if "taxi" in text or "cab" in text:
        modes.add("rideshare")
    if "not sure" in text or "recommend" in text:
        return []
    return sorted(modes)


def _parse_duration(raw: str, duration_days: float | None = None) -> DurationAnalysis:
    text = raw.lower()
    days: float | None = duration_days
    match = re.search(r"(\d+(?:\.\d+)?)\s*(day|days|night|nights)", text)
    if days is None and match:
        days = float(match.group(1))
    elif days is None and "week" in text:
        week_match = re.search(r"(\d+(?:\.\d+)?)\s*week", text)
        days = 7 * float(week_match.group(1)) if week_match else 7
    elif days is None and "overnight" in text:
        days = 2
    elif days is None and re.search(r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs)", text):
        days = 0.5

    if days is None:
        band = "unknown"
    elif days <= 1:
        band = "short"
    elif days <= 3:
        band = "medium"
    elif days <= 7:
        band = "long"
    else:
        band = "multi_day"

    considerations = {
        "short": ["Short trips reduce, but do not remove, battery and medication planning needs."],
        "medium": ["Medium trips may require seating, medication, and transfer planning."],
        "long": ["Long trips make device batteries, service-animal relief, and rest planning more important."],
        "multi_day": ["Multi-day trips need explicit planning for rest, medication, equipment, and service-animal care."],
        "unknown": ["Duration was unclear, so duration-sensitive needs should be confirmed directly."],
    }[band]
    return DurationAnalysis(raw=raw, days=days, band=band, duration_considerations=considerations)


def _score_provider(provider: ProviderRecord, needs: list[str], band: str) -> int:
    category_matches = len(set(provider.categories) & set(needs))
    score = 35 + category_matches * 12
    if band in provider.duration_relevant.best_for_duration_bands:
        score += 15
    if provider.mode == "rail" and band in {"long", "multi_day"}:
        score += 8
    return min(100, score)


def _looks_international(text: str) -> bool:
    international_terms = [
        "international",
        "passport",
        "canada",
        "mexico",
        "europe",
        "london",
        "paris",
        "tokyo",
        "toronto",
        "vancouver",
    ]
    return any(term in text for term in international_terms)
