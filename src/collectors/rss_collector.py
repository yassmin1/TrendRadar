"""RSS feed collector."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Iterable

try:
    import feedparser
except ModuleNotFoundError:  # pragma: no cover - depends on optional install
    feedparser = None

from src.processing.normalize_schema import normalize_free_source_records


class RSSCollector:
    """Collect public RSS/Atom feed entries."""

    def __init__(self, feed_urls: Iterable[str]) -> None:
        self.feed_urls = [url for url in feed_urls if url]

    def collect_dataframe(self, query: str | None = None, max_entries_per_feed: int = 25):
        """Collect feed entries and optionally filter by query text."""
        if feedparser is None:
            raise RuntimeError("RSS collection requires feedparser. Install dependencies with `pip install -r requirements.txt`.")
        records = []
        query_lower = query.lower() if query else None
        for feed_url in self.feed_urls:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title") or feed_url
            for entry in feed.entries[:max_entries_per_feed]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                text = f"{title} {summary}"
                if query_lower and query_lower not in text.lower():
                    continue
                records.append(
                    {
                        "platform": "rss",
                        "source_type": "rss_entry",
                        "source_name": source_name,
                        "source_id": feed_url,
                        "post_id": entry.get("id") or entry.get("link"),
                        "created_at": _entry_datetime(entry),
                        "title": title,
                        "text": text,
                        "url": entry.get("link"),
                        "topic": query,
                    }
                )
        return normalize_free_source_records(records, topic=query)


def _entry_datetime(entry) -> str:
    for key in ("published", "updated", "created"):
        if entry.get(key):
            try:
                return parsedate_to_datetime(entry[key]).astimezone(UTC).isoformat()
            except (TypeError, ValueError):
                pass
    return datetime.now(UTC).isoformat()
