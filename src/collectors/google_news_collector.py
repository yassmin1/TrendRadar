"""Google News RSS keyword-search collector."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call


class GoogleNewsCollector:
    """Collect keyword-matched articles from Google's public News RSS search."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        root = ElementTree.fromstring(self._request(url))
        records = []
        for item in root.findall("./channel/item")[: self.settings.free_source_max_records]:
            link = item.findtext("link")
            title = item.findtext("title") or ""
            source = item.findtext("source") or "Google News"
            published = item.findtext("pubDate")
            records.append(
                {
                    "platform": "google_news",
                    "source_type": "news_article",
                    "source_name": source,
                    "source_id": source,
                    "post_id": link,
                    "created_at": _rss_datetime(published),
                    "title": title,
                    "text": title,
                    "url": link,
                    "topic": query,
                }
            )
        return normalize_free_source_records(records, topic=query)

    @retry_api_call()
    def _request(self, url: str) -> bytes:
        response = requests.get(url, timeout=self.settings.request_timeout_seconds, headers={"User-Agent": "social-media-trend-tracker/1.0"})
        if response.status_code >= 500:
            raise ConnectionError(f"Google News server error: {response.status_code}")
        response.raise_for_status()
        return response.content


def _rss_datetime(value: str | None) -> str:
    if value:
        try:
            return parsedate_to_datetime(value).astimezone(UTC).isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.now(UTC).isoformat()
