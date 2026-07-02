"""Hacker News public API collector."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsCollector:
    """Collect public top Hacker News stories from the free Firebase API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str | None = None, max_items: int | None = None):
        """Search Hacker News directly instead of filtering only the front-page stories."""
        max_items = max_items or self.settings.free_source_max_records
        if query:
            page = self._get_json(HN_SEARCH_URL, params={"query": query, "tags": "story", "hitsPerPage": min(max(max_items, 1), 100)})
            stories = page.get("hits", [])
        else:
            ids = self._get_json(f"{HN_BASE}/topstories.json")[:max_items]
            stories = [self._get_json(f"{HN_BASE}/item/{story_id}.json") for story_id in ids]
        records = []
        for story in stories:
            title = story.get("title", "")
            timestamp = story.get("time") or story.get("created_at")
            created_at = datetime.fromtimestamp(timestamp, tz=UTC).isoformat() if isinstance(timestamp, (int, float)) else timestamp or datetime.now(UTC).isoformat()
            records.append(
                {
                    "platform": "hackernews",
                    "source_type": "story",
                    "source_name": story.get("by") or story.get("author"),
                    "source_id": story.get("by") or story.get("author"),
                    "post_id": str(story.get("id") or story.get("objectID")),
                    "created_at": created_at,
                    "title": title,
                    "text": title,
                    "url": story.get("url") or f"https://news.ycombinator.com/item?id={story.get('id') or story.get('objectID')}",
                    "topic": query,
                    "like_count": story.get("score", story.get("points", 0)),
                    "comment_count": story.get("descendants", story.get("num_comments", 0)),
                    "engagement_count": int(story.get("score", story.get("points", 0)) or 0) + int(story.get("descendants", story.get("num_comments", 0)) or 0),
                }
            )
        return normalize_free_source_records(records, topic=query)

    @retry_api_call()
    def _get_json(self, url: str, params: dict | None = None):
        response = requests.get(url, params=params, timeout=self.settings.request_timeout_seconds)
        if response.status_code >= 500:
            raise ConnectionError(f"Hacker News API server error: {response.status_code}")
        response.raise_for_status()
        return response.json()
