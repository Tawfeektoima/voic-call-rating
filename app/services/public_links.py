from __future__ import annotations

from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from app.config import Settings


def normalize_public_base_url(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("PUBLIC_BASE_URL must be an absolute http(s) URL.")
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def normalize_public_path(path_value: str | None) -> str:
    normalized = (path_value or "").strip() or "/interview-portal"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def validate_public_url_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    try:
        normalize_public_path(settings.INTERVIEW_PORTAL_PATH)
        normalize_public_base_url(settings.FRONTEND_URL)
        if settings.PUBLIC_BASE_URL.strip():
            normalize_public_base_url(settings.PUBLIC_BASE_URL)
        elif settings.REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS:
            errors.append("PUBLIC_BASE_URL is required when REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS=true.")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def get_effective_public_base_url(settings: Settings) -> str:
    configured = normalize_public_base_url(settings.PUBLIC_BASE_URL)
    if configured:
        return configured
    return normalize_public_base_url(settings.FRONTEND_URL)


def build_interview_invite_url(session_token: str, settings: Settings) -> str | None:
    base_url = get_effective_public_base_url(settings)
    if not base_url:
        if settings.REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS:
            raise ValueError("PUBLIC_BASE_URL is required before creating interview invites.")
        return None
    portal_path = normalize_public_path(settings.INTERVIEW_PORTAL_PATH)
    parsed = urlparse(base_url)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            portal_path,
            "",
            urlencode({"token": session_token}),
            "",
        )
    )


def get_additional_allowed_origins(settings: Settings) -> list[str]:
    origins: list[str] = []
    for candidate in (settings.FRONTEND_URL, settings.PUBLIC_BASE_URL):
        try:
            normalized = normalize_public_base_url(candidate)
        except ValueError:
            continue
        if normalized and normalized not in origins:
            origins.append(normalized)
    return origins


def probe_public_base_url(base_url: str, timeout_seconds: float = 3.0) -> tuple[bool, str]:
    normalized = normalize_public_base_url(base_url)
    request = Request(normalized, method="HEAD")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return True, f"HTTP {response.status}"
    except HTTPError as exc:
        if exc.code in {401, 403, 404, 405}:
            return True, f"Reachable with HTTP {exc.code}"
        return False, f"HTTP {exc.code}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, str(exc)
