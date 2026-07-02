"""OpenAlex public works keyword-search collector."""

from __future__ import annotations

import requests

from src.processing.normalize_schema import normalize_free_source_records


class OpenAlexCollector:
    """Collect public scholarly works from OpenAlex."""

    API_URL = "https://api.openalex.org/works"

    def __init__(self, settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        max_records = min(max(self.settings.free_source_max_records, 1), 200)
        response = requests.get(
            self.API_URL,
            params={
                "search": query,
                "per-page": max_records,
                "sort": "publication_date:desc",
            },
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": "SocialMediaTrendTracker/1.0"},
        )
        response.raise_for_status()
        records = []
        for item in response.json().get("results", []):
            source = (item.get("primary_location") or {}).get("source") or {}
            author_names = [
                ((authorship.get("author") or {}).get("display_name") or "")
                for authorship in item.get("authorships", [])
            ]
            cited_by_count = int(item.get("cited_by_count", 0) or 0)
            title = item.get("display_name") or ""
            publication_date = item.get("publication_date")
            records.append(
                {
                    "platform": "openalex",
                    "source_type": item.get("type") or "work",
                    "source_name": source.get("display_name") or ", ".join(name for name in author_names[:3] if name) or "OpenAlex",
                    "source_id": source.get("id") or item.get("host_venue", {}).get("id"),
                    "post_id": item.get("id"),
                    "created_at": f"{publication_date}T00:00:00Z" if publication_date else None,
                    "title": title,
                    "text": title,
                    "url": item.get("doi") or item.get("id"),
                    "topic": query,
                    "language": item.get("language"),
                    "engagement_count": cited_by_count,
                    "share_count": cited_by_count,
                }
            )
        return normalize_free_source_records(records, topic=query)
