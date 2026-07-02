"""Wikinews public search collector."""

from __future__ import annotations

import requests

from src.processing.normalize_schema import normalize_free_source_records


class WikinewsCollector:
    """Collect public Wikinews pages matching a keyword query."""

    API_URL = "https://en.wikinews.org/w/api.php"

    def __init__(self, settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        max_records = min(max(self.settings.free_source_max_records, 1), 50)
        response = requests.get(
            self.API_URL,
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": max_records,
                "srprop": "timestamp|snippet|size|wordcount",
            },
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": "SocialMediaTrendTracker/1.0"},
        )
        response.raise_for_status()
        records = []
        for page in response.json().get("query", {}).get("search", []):
            page_id = str(page.get("pageid") or "")
            title = page.get("title") or ""
            url_title = title.replace(" ", "_")
            records.append(
                {
                    "platform": "wikinews",
                    "source_type": "news_page",
                    "source_name": "Wikinews",
                    "source_id": "en.wikinews.org",
                    "post_id": page_id,
                    "created_at": page.get("timestamp"),
                    "title": title,
                    "text": f"{title} {page.get('snippet', '')}",
                    "url": f"https://en.wikinews.org/wiki/{url_title}" if title else None,
                    "topic": query,
                    "language": "en",
                    "engagement_count": int(page.get("wordcount", 0) or 0),
                    "view_count": int(page.get("size", 0) or 0),
                }
            )
        return normalize_free_source_records(records, topic=query)
