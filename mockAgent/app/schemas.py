from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


NeedTag = Literal[
    "mobility",
    "vision",
    "hearing",
    "sensory",
    "cognitive",
    "service_animal",
    "medical",
    "other",
]

RecommendationStatus = Literal[
    "ok",
    "no_strong_match",
    "mode_conflict",
    "unsupported_region",
    "needs_clarification",
]

Mode = Literal["air", "rail", "rideshare", "taxi", "not_sure", "unsupported"]
DurationBand = Literal["short", "medium", "long", "multi_day", "unknown"]


class RouteLocation(BaseModel):
    id: str
    code: str
    name: str
    city: str
    state: str
    type: str
    lat: float
    lng: float


class RecommendationRequest(BaseModel):
    needs_description: str = Field(
        default="",
        max_length=1200,
        description="Optional free-text details. v1 UI primarily uses quick tags.",
    )
    transport_modes: list[Mode] = Field(default_factory=list)
    origin: RouteLocation | None = None
    destination: RouteLocation | None = None
    duration_days: float | None = Field(default=None, ge=0.25, le=60)
    transport_preferences: str | None = Field(
        default=None,
        max_length=1000,
        description="Backward-compatible transport preference text.",
    )
    trip_duration: str = Field(
        default="",
        min_length=0,
        max_length=100,
        description="Duration label such as '2 days' or '8+ days'.",
    )
    quick_tags: list[NeedTag] = Field(default_factory=list)
    plain_language: bool = False

    @field_validator("needs_description", "transport_preferences", "trip_duration")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("needs_description")
    @classmethod
    def allow_empty_but_cap_length(cls, value: str) -> str:
        return value.strip()


class LegacyRecommendationRequest(BaseModel):
    needs_description: str = Field(
        default="",
        min_length=0,
        max_length=4000,
        description="Free-text accessibility needs or disability context.",
    )
    transport_preferences: str | None = Field(
        default=None,
        max_length=1000,
        description="Free-text transport preference, or not sure.",
    )
    trip_duration: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Duration only, such as '5 days' or 'overnight'.",
    )
    quick_tags: list[NeedTag] = Field(default_factory=list)
    plain_language: bool = False

    @field_validator("needs_description", "transport_preferences", "trip_duration")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"]


class DurationAnalysis(BaseModel):
    raw: str
    days: float | None = None
    band: DurationBand
    duration_considerations: list[str] = Field(default_factory=list)


class ProviderRecommendation(BaseModel):
    provider_id: str
    provider_name: str = ""
    mode: str = ""
    score: int = Field(ge=0, le=100)
    why_recommended: list[str] = Field(default_factory=list)
    watchouts: list[str] = Field(default_factory=list)
    policy_url: str = ""
    booking_url: str = ""
    logo_url: str = ""


class RecommendationResult(BaseModel):
    status: RecommendationStatus
    detected_needs: list[str] = Field(default_factory=list)
    requested_modes: list[str] = Field(default_factory=list)
    recommended_mode: Mode | None = None
    duration: DurationAnalysis
    summary: str
    providers: list[ProviderRecommendation] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    disclaimer: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "expired", "not_found"]
    result: RecommendationResult | None = None
    error: str | None = None


class DurationRelevant(BaseModel):
    powered_mobility: str
    service_animal_relief: str
    medical_equipment_medication: str
    seating_rest: str
    best_for_duration_bands: list[DurationBand]
    duration_notes: str


class ProviderRecord(BaseModel):
    id: str
    name: str
    mode: Literal["air", "rail", "rideshare"]
    categories: list[str]
    accessibility_features: list[str]
    accommodation_summary: str
    duration_relevant: DurationRelevant
    policy_url: str
    booking_url: str
    logo_url: str
    source_checked_at: str
    notes: str | None = None

    def llm_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "categories": self.categories,
            "accessibility_features": self.accessibility_features,
            "accommodation_summary": self.accommodation_summary,
            "duration_relevant": self.duration_relevant.model_dump(),
            "policy_url": self.policy_url,
            "booking_url": self.booking_url,
            "logo_url": self.logo_url,
            "notes": self.notes,
        }
