"""Twitter/X API v2 recent-search collector."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.processing.normalize_schema import normalize_x_posts
from src.utils.config import Settings
from src.utils.cost_control import DailyRequestBudget, JsonResponseCache
from src.utils.retry import AccessDeniedError, RateLimitError, retry_api_call

LOGGER = logging.getLogger(__name__)
X_RECENT_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class XCollector:
    """Collect public X posts through the official X API v2 recent search endpoint."""

    def __init__(self, settings: Settings, raw_dir: str | Path = "data/raw/x") -> None:
        self.settings = settings
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cache = JsonResponseCache()
        self.budget = DailyRequestBudget("x_api", settings.x_daily_request_budget)

    def search(
        self,
        query: str,
        max_results: int = 100,
        max_pages: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        language: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Search public posts by keyword/hashtag and return raw pages plus tweet records."""
        if not self.settings.x_bearer_token:
            raise AccessDeniedError("Missing X_BEARER_TOKEN. Set it in .env to use live X collection.")

        effective_query = f"({query})"
        if language:
            effective_query = f"{effective_query} lang:{language}"

        params: dict[str, Any] = {
            "query": effective_query,
            "max_results": min(max(max_results, 10), 100),
            "tweet.fields": "id,text,author_id,created_at,lang,public_metrics,entities,conversation_id",
            "expansions": "author_id",
            "user.fields": "id,name,username,public_metrics,verified",
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        page_limit = max_pages or self.settings.max_pages_per_query
        cache_key = {
            "query": effective_query,
            "max_results": params["max_results"],
            "start_time": start_time,
            "end_time": end_time,
            "language": language,
            "max_pages": page_limit,
        }
        cached_pages = self.cache.load("x_recent_search", cache_key, self.settings.x_cache_ttl_minutes)
        if cached_pages is not None:
            LOGGER.info("Using cached X response for query %s", query)
            records = [record for page in cached_pages for record in page.get("data", [])]
            return cached_pages, records

        pages: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        next_token: str | None = None

        for _ in range(page_limit):
            if next_token:
                params["next_token"] = next_token
            self.budget.consume(1)
            page = self._request(params)
            pages.append(page)
            records.extend(page.get("data", []))
            next_token = page.get("meta", {}).get("next_token")
            if not next_token:
                break
            time.sleep(1)

        self._save_raw(query, pages)
        self.cache.save("x_recent_search", cache_key, pages)
        return pages, records

    def collect_dataframe(self, query: str, **kwargs: Any):
        """Search and normalize results into the unified schema."""
        _, records = self.search(query=query, **kwargs)
        return normalize_x_posts(records, topic=query)

    @retry_api_call()
    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.settings.x_bearer_token}"}
        response = requests.get(
            X_RECENT_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=self.settings.request_timeout_seconds,
        )
        if response.status_code == 429:
            reset_at = response.headers.get("x-rate-limit-reset")
            wait_seconds = max(int(reset_at) - int(time.time()), 60) if reset_at else 900
            LOGGER.warning("X API rate limit reached; retrying after %s seconds", wait_seconds)
            time.sleep(min(wait_seconds, 900))
            raise RateLimitError("X API rate limit reached")
        if response.status_code in {401, 402, 403}:
            raise AccessDeniedError(f"X API access denied: {response.status_code} {response.text[:250]}")
        if response.status_code >= 500:
            raise ConnectionError(f"X API server error: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _save_raw(self, query: str, pages: list[dict[str, Any]]) -> Path:
        safe_query = "".join(ch if ch.isalnum() else "_" for ch in query)[:80]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = self.raw_dir / f"x_{safe_query}_{timestamp}.json"
        path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
        LOGGER.info("Saved raw X response to %s", path)
        return path
