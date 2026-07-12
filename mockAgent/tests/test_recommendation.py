import json

from app.providers import load_providers
from app.recommendation import build_local_recommendation, parse_and_validate_llm_result
from app.schemas import RecommendationRequest


def test_provider_dataset_has_required_urls_and_logo_paths():
    providers = load_providers()

    assert len(providers) >= 9
    for provider in providers:
        assert provider.policy_url.startswith("https://")
        assert provider.booking_url.startswith("https://")
        assert provider.logo_url.startswith("/logos/")
        assert provider.duration_relevant.powered_mobility
        assert provider.duration_relevant.service_animal_relief
        assert provider.duration_relevant.medical_equipment_medication
        assert provider.duration_relevant.seating_rest


def test_llm_result_is_sanitized_to_dataset_links():
    provider = load_providers()[0]
    raw = json.dumps(
        {
            "status": "ok",
            "detected_needs": ["mobility"],
            "requested_modes": ["air"],
            "recommended_mode": "air",
            "duration": {
                "raw": "2 days",
                "days": 2,
                "band": "medium",
                "duration_considerations": ["Medium trip."],
            },
            "summary": "Candidate match.",
            "providers": [
                {
                    "provider_id": provider.id,
                    "provider_name": "Wrong name",
                    "mode": "wrong",
                    "score": 90,
                    "why_recommended": ["Mobility support."],
                    "watchouts": ["Confirm route."],
                    "policy_url": "https://example.com/bad-policy",
                    "booking_url": "https://example.com/bad-booking",
                    "logo_url": "https://example.com/bad-logo.svg",
                }
            ],
            "next_steps": ["Confirm directly."],
            "disclaimer": "Bad disclaimer.",
        }
    )

    result = parse_and_validate_llm_result(raw, load_providers())

    assert result.providers[0].provider_name == provider.name
    assert result.providers[0].mode == provider.mode
    assert result.providers[0].policy_url == provider.policy_url
    assert result.providers[0].booking_url == provider.booking_url
    assert result.providers[0].logo_url == provider.logo_url
    assert "Accommodation policies can change" in result.disclaimer


def test_fake_recommendation_handles_international_scope():
    request = RecommendationRequest(
        needs_description="I use a wheelchair and am going to London.",
        transport_preferences="flight",
        trip_duration="5 days",
        quick_tags=["mobility"],
        plain_language=True,
    )

    result = build_local_recommendation(request, load_providers())

    assert result.status == "unsupported_region"
    assert result.providers == []


def test_fake_recommendation_returns_dataset_provider_for_mobility_train_trip():
    request = RecommendationRequest(
        needs_description="I use a wheelchair and need space to stay in my chair.",
        transport_preferences="train",
        trip_duration="6 days",
        quick_tags=["mobility"],
        plain_language=True,
    )

    result = build_local_recommendation(request, load_providers())

    assert result.status == "ok"
    assert result.providers
    assert result.providers[0].provider_id == "amtrak"

