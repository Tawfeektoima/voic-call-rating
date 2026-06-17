from types import SimpleNamespace

from app.services.public_links import build_interview_invite_url, validate_public_url_settings


def test_build_interview_invite_url_prefers_public_base_url():
    settings = SimpleNamespace(
        FRONTEND_URL="http://localhost:5173",
        PUBLIC_BASE_URL="https://interviews.example.com",
        INTERVIEW_PORTAL_PATH="/interview-portal",
        REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=False,
    )

    assert build_interview_invite_url("abc123", settings) == "https://interviews.example.com/interview-portal?token=abc123"


def test_validate_public_url_settings_requires_public_base_when_strict():
    settings = SimpleNamespace(
        FRONTEND_URL="http://localhost:5173",
        PUBLIC_BASE_URL="",
        INTERVIEW_PORTAL_PATH="/interview-portal",
        REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=True,
    )

    errors = validate_public_url_settings(settings)
    assert errors == ["PUBLIC_BASE_URL is required when REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=true."]
