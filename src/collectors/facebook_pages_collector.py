"""Optional Facebook Pages collector.

This collector is intentionally limited to approved Page Public Content Access
or page tokens the operator is authorized to use. It never attempts private
profiles, private groups, restricted users, or non-public content.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.processing.clean_text import clean_text, extract_hashtags, extract_mentions, extract_urls
from src.processing.normalize_schema import ensure_unified_columns, to_utc, utc_now_iso
from src.utils.config import Settings
from src.utils.retry import AccessDeniedError, RateLimitError, retry_api_call

LOGGER = logging.getLogger(__name__)
GRAPH_BASE = "https://graph.facebook.com/v20.0"


class FacebookPagesCollector:
    """Collect approved public Facebook Page posts when access is available."""

    def __init__(self, settings: Settings, raw_dir: str | Path = "data/raw/facebook_pages") -> None:
        self.settings = settings
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def collect_page_posts(self, page_id: str, limit: int = 100) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Collect public posts for an approved page ID."""
        token = self.settings.facebook_page_access_token or self.settings.meta_access_token
        if not token:
            raise AccessDeniedError("Missing FACEBOOK_PAGE_ACCESS_TOKEN or META_ACCESS_TOKEN for optional Page collection.")
        url = f"{GRAPH_BASE}/{page_id}/posts"
        params = {
            "access_token": token,
            "fields": "id,message,created_time,permalink_url,shares,comments.summary(true),reactions.summary(true)",
            "limit": min(limit, 100),
        }
        page = self._request(url, params)
        pages = [page]
        records = page.get("data", [])
        self._save_raw(page_id, pages)
        return pages, records

    def collect_dataframe(self, page_id: str, topic: str | None = None):
        """Collect and normalize approved Facebook Page posts."""
        _, records = self.collect_page_posts(page_id)
        collected_at = utc_now_iso()
        rows = []
        for record in records:
            text = record.get("message", "")
            comment_count = record.get("comments", {}).get("summary", {}).get("total_count", 0)
            like_count = record.get("reactions", {}).get("summary", {}).get("total_count", 0)
            share_count = record.get("shares", {}).get("count", 0)
            rows.append(
                {
                    "platform": "facebook",
                    "source_type": "page_post",
                    "source_name": page_id,
                    "source_id": page_id,
                    "post_id": record.get("id"),
                    "created_at": to_utc(record.get("created_time")),
                    "text": clean_text(text),
                    "language": None,
                    "url": record.get("permalink_url"),
                    "hashtags": extract_hashtags(text),
                    "mentions": extract_mentions(text),
                    "shared_links": extract_urls(text),
                    "engagement_count": int(comment_count or 0) + int(like_count or 0) + int(share_count or 0),
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "share_count": share_count,
                    "view_count": 0,
                    "impression_count": 0,
                    "country": None,
                    "topic": topic,
                    "sentiment_label": None,
                    "sentiment_score": None,
                    "collected_at": collected_at,
                }
            )
        return ensure_unified_columns(pd.DataFrame(rows))

    @retry_api_call()
    def _request(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(url, params=params, timeout=self.settings.request_timeout_seconds)
        if response.status_code == 429:
            raise RateLimitError("Facebook Graph API rate limit reached")
        if response.status_code in {400, 401, 402, 403}:
            raise AccessDeniedError(f"Facebook Page access denied or unavailable: {response.status_code} {response.text[:250]}")
        if response.status_code >= 500:
            raise ConnectionError(f"Facebook Graph API server error: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _save_raw(self, page_id: str, pages: list[dict[str, Any]]) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = self.raw_dir / f"facebook_page_{page_id}_{timestamp}.json"
        path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
        LOGGER.info("Saved raw Facebook Page response to %s", path)
        return path
