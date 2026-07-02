"""Public Reddit keyword-search collector."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"


class RedditCollector:
    """Collect public Reddit posts through its unauthenticated JSON search endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        page = self._request({"q": query, "sort": "new", "t": "week", "limit": min(max(self.settings.free_source_max_records, 1), 100), "raw_json": 1})
        records = []
        for child in page.get("data", {}).get("children", []):
            post = child.get("data", {})
            post_id = post.get("id")
            records.append({
                "platform": "reddit", "source_type": "post", "source_name": post.get("subreddit_name_prefixed"),
                "source_id": post.get("subreddit"), "post_id": post_id,
                "created_at": datetime.fromtimestamp(post.get("created_utc", 0), tz=UTC).isoformat() if post.get("created_utc") else None,
                "title": post.get("title", ""), "text": f"{post.get('title', '')} {post.get('selftext', '')}",
                "url": f"https://www.reddit.com{post.get('permalink')}" if post.get("permalink") else post.get("url"),
                "topic": query, "like_count": post.get("score", 0), "comment_count": post.get("num_comments", 0),
                "engagement_count": int(post.get("score", 0) or 0) + int(post.get("num_comments", 0) or 0),
            })
        return normalize_free_source_records(records, topic=query)

    @retry_api_call()
    def _request(self, params: dict) -> dict:
        response = requests.get(REDDIT_SEARCH_URL, params=params, headers={"User-Agent": "social-media-trend-tracker/1.0"}, timeout=self.settings.request_timeout_seconds)
        if response.status_code >= 500:
            raise ConnectionError(f"Reddit server error: {response.status_code}")
        response.raise_for_status()
        return response.json()
