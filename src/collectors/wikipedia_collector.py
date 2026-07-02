"""Wikipedia Pageviews collector."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Iterable
from urllib.parse import quote

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call

LOGGER = logging.getLogger(__name__)


class WikipediaPageviewsCollector:
    """Collect free public pageview counts for configured Wikipedia articles."""

    def __init__(self, settings: Settings, project: str = "en.wikipedia.org") -> None:
        self.settings = settings
        self.project = project

    def collect_dataframe(self, articles: Iterable[str], days: int = 7):
        """Collect recent pageviews for article titles."""
        end = datetime.now(UTC).date() - timedelta(days=1)
        start = end - timedelta(days=max(days - 1, 0))
        records = []
        for article in [item for item in articles if item]:
            page = self._request(article, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
            views = sum(item.get("views", 0) for item in page.get("items", []))
            records.append(
                {
                    "platform": "wikipedia",
                    "source_type": "pageviews",
                    "source_name": "Wikipedia",
                    "source_id": self.project,
                    "post_id": f"{self.project}:{article}:{start}:{end}",
                    "created_at": datetime.combine(end, datetime.min.time(), tzinfo=UTC).isoformat(),
                    "title": article,
                    "text": f"Wikipedia pageviews for {article}",
                    "url": f"https://{self.project}/wiki/{quote(article.replace(' ', '_'))}",
                    "topic": article,
                    "view_count": views,
                    "engagement_count": views,
                }
            )
        return normalize_free_source_records(records)

    @retry_api_call()
    def _request(self, article: str, start: str, end: str) -> dict:
        encoded = quote(article.replace(" ", "_"), safe="")
        url = (
            "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"{self.project}/all-access/user/{encoded}/daily/{start}/{end}"
        )
        response = requests.get(url, timeout=self.settings.request_timeout_seconds, headers={"User-Agent": "social-media-trend-tracker/1.0"})
        if response.status_code == 404:
            LOGGER.warning("No Wikipedia pageviews found for %s", article)
            return {"items": []}
        if response.status_code >= 500:
            raise ConnectionError(f"Wikipedia server error: {response.status_code}")
        response.raise_for_status()
        return response.json()
