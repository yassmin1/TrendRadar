"""Meta Ad Library collector for public ads."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.processing.normalize_schema import normalize_meta_ads
from src.utils.config import Settings
from src.utils.retry import AccessDeniedError, RateLimitError, retry_api_call

LOGGER = logging.getLogger(__name__)
META_AD_LIBRARY_URL = "https://graph.facebook.com/v20.0/ads_archive"


class MetaAdLibraryCollector:
    """Collect public ad records from Meta Ad Library API."""

    def __init__(self, settings: Settings, raw_dir: str | Path = "data/raw/meta_ads") -> None:
        self.settings = settings
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def search(
        self,
        keyword: str,
        country: str | None = None,
        active_status: str = "ALL",
        ad_reached_countries: list[str] | None = None,
        delivery_date_min: str | None = None,
        delivery_date_max: str | None = None,
        page_id: str | None = None,
        max_pages: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Search public ads by keyword and public ad-library filters."""
        if not self.settings.meta_access_token:
            raise AccessDeniedError("Missing META_ACCESS_TOKEN. Set it in .env to use Meta Ad Library collection.")

        params: dict[str, Any] = {
            "access_token": self.settings.meta_access_token,
            "search_terms": keyword,
            "ad_type": "ALL",
            "ad_active_status": active_status,
            "ad_reached_countries": ad_reached_countries or [country or self.settings.default_country],
            "fields": ",".join(
                [
                    "id",
                    "ad_archive_id",
                    "page_id",
                    "page_name",
                    "ad_delivery_start_time",
                    "ad_delivery_stop_time",
                    "ad_creative_bodies",
                    "ad_creative_link_titles",
                    "ad_creative_link_descriptions",
                    "ad_snapshot_url",
                    "currency",
                    "impressions",
                    "spend",
                    "targeted_or_reached_countries",
                ]
            ),
            "limit": 100,
        }
        if delivery_date_min:
            params["ad_delivery_date_min"] = delivery_date_min
        if delivery_date_max:
            params["ad_delivery_date_max"] = delivery_date_max
        if page_id:
            params["search_page_ids"] = [page_id]

        pages: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        url: str | None = META_AD_LIBRARY_URL
        page_limit = max_pages or self.settings.max_pages_per_query

        for _ in range(page_limit):
            page = self._request(url, params if url == META_AD_LIBRARY_URL else None)
            pages.append(page)
            records.extend(page.get("data", []))
            url = page.get("paging", {}).get("next")
            if not url:
                break
            time.sleep(1)

        self._save_raw(keyword, pages)
        return pages, records

    def collect_dataframe(self, keyword: str, **kwargs: Any):
        """Search and normalize Meta ads into the unified schema."""
        _, records = self.search(keyword=keyword, **kwargs)
        return normalize_meta_ads(records, topic=keyword)

    @retry_api_call()
    def _request(self, url: str | None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not url:
            return {"data": []}
        response = requests.get(url, params=params, timeout=self.settings.request_timeout_seconds)
        if response.status_code == 429:
            LOGGER.warning("Meta API rate limit reached")
            raise RateLimitError("Meta API rate limit reached")
        if response.status_code in {400, 401, 402, 403}:
            raise AccessDeniedError(f"Meta API access denied or invalid request: {response.status_code} {response.text[:250]}")
        if response.status_code >= 500:
            raise ConnectionError(f"Meta API server error: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _save_raw(self, keyword: str, pages: list[dict[str, Any]]) -> Path:
        safe_keyword = "".join(ch if ch.isalnum() else "_" for ch in keyword)[:80]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = self.raw_dir / f"meta_ads_{safe_keyword}_{timestamp}.json"
        path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
        LOGGER.info("Saved raw Meta Ad Library response to %s", path)
        return path
