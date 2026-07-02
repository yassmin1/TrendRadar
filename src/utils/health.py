"""API health checks for configured collectors."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from src.utils.config import Settings


def check_api_health(settings: Settings, include_meta: bool = False) -> list[dict[str, Any]]:
    """Return lightweight API readiness checks without collecting full datasets."""
    checks = [_check_x(settings)]
    if include_meta:
        checks.append(_check_meta(settings))
    else:
        checks.append(
            {
                "service": "meta_ad_library",
                "status": "disabled",
                "detail": "Meta collection is disabled. Use --include-meta or COLLECT_META=true.",
                "checked_at": _now(),
            }
        )
    return checks


def _check_x(settings: Settings) -> dict[str, Any]:
    if not settings.x_bearer_token:
        return _result("x_api", "missing_token", "X_BEARER_TOKEN is not set.")
    try:
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers={"Authorization": f"Bearer {settings.x_bearer_token}"},
            params={
                "query": "test",
                "max_results": 10,
                "tweet.fields": "id",
            },
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code == 200:
            return _result("x_api", "ok", "Recent search endpoint is accessible.")
        if response.status_code == 402:
            return _result("x_api", "no_credits", response.text[:500])
        if response.status_code in {401, 403}:
            return _result("x_api", "access_denied", response.text[:500])
        if response.status_code == 429:
            return _result("x_api", "rate_limited", response.text[:500])
        return _result("x_api", "error", f"HTTP {response.status_code}: {response.text[:500]}")
    except requests.RequestException as exc:
        return _result("x_api", "error", str(exc))


def _check_meta(settings: Settings) -> dict[str, Any]:
    if not settings.meta_access_token:
        return _result("meta_ad_library", "missing_token", "META_ACCESS_TOKEN is not set.")
    try:
        response = requests.get(
            "https://graph.facebook.com/v20.0/ads_archive",
            params={
                "access_token": settings.meta_access_token,
                "search_terms": "test",
                "ad_type": "ALL",
                "ad_reached_countries": [settings.default_country],
                "fields": "id,page_id,page_name",
                "limit": 1,
            },
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code == 200:
            return _result("meta_ad_library", "ok", "Ad Library endpoint is accessible.")
        if response.status_code in {400, 401, 403}:
            return _result("meta_ad_library", "access_denied", response.text[:500])
        if response.status_code == 429:
            return _result("meta_ad_library", "rate_limited", response.text[:500])
        return _result("meta_ad_library", "error", f"HTTP {response.status_code}: {response.text[:500]}")
    except requests.RequestException as exc:
        return _result("meta_ad_library", "error", str(exc))


def _result(service: str, status: str, detail: str) -> dict[str, Any]:
    return {"service": service, "status": status, "detail": detail, "checked_at": _now()}


def _now() -> str:
    return datetime.now(UTC).isoformat()
