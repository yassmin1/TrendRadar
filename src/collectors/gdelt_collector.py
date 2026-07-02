"""GDELT public news collector."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call

LOGGER = logging.getLogger(__name__)
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTCollector:
    """Collect public news article metadata from the free GDELT DOC API."""

    def __init__(self, settings: Settings, raw_dir: str | Path = "data/raw/gdelt") -> None:
        self.settings = settings
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def collect_dataframe(self, query: str, max_records: int | None = None):
        """Collect and normalize GDELT article records."""
        max_records = max_records or self.settings.free_source_max_records
        page = self._request(
            {
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": min(max(max_records, 1), 250),
                "sort": "HybridRel",
            }
        )
        self._save_raw(query, page)
        records = []
        for article in page.get("articles", []):
            records.append(
                {
                    "platform": "gdelt",
                    "source_type": "news_article",
                    "source_name": article.get("domain"),
                    "source_id": article.get("domain"),
                    "post_id": article.get("url"),
                    "created_at": article.get("seendate"),
                    "title": article.get("title", ""),
                    "text": f"{article.get('title', '')} {article.get('sourcecountry', '')}",
                    "language": article.get("language"),
                    "url": article.get("url"),
                    "country": article.get("sourcecountry"),
                    "topic": query,
                    "engagement_count": 0,
                }
            )
        return normalize_free_source_records(records, topic=query)

    @retry_api_call()
    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(GDELT_DOC_URL, params=params, timeout=self.settings.request_timeout_seconds)
        if response.status_code >= 500:
            raise ConnectionError(f"GDELT server error: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _save_raw(self, query: str, page: dict[str, Any]) -> Path:
        safe_query = "".join(ch if ch.isalnum() else "_" for ch in query)[:80]
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = self.raw_dir / f"gdelt_{safe_query}_{timestamp}.json"
        path.write_text(json.dumps(page, indent=2), encoding="utf-8")
        LOGGER.info("Saved raw GDELT response to %s", path)
        return path
