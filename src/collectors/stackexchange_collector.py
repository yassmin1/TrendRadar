"""Stack Exchange keyword-search collector."""

from __future__ import annotations

from datetime import UTC, datetime

import requests

from src.processing.normalize_schema import normalize_free_source_records
from src.utils.config import Settings
from src.utils.retry import retry_api_call

STACKEXCHANGE_SEARCH_URL = "https://api.stackexchange.com/2.3/search/advanced"


class StackExchangeCollector:
    """Collect public question discussions from the Stack Exchange network."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        page = self._request({"site": "stackoverflow", "q": query, "order": "desc", "sort": "activity", "pagesize": min(max(self.settings.free_source_max_records, 1), 100)})
        records = []
        for question in page.get("items", []):
            owner = question.get("owner", {})
            records.append({
                "platform": "stackexchange", "source_type": "question", "source_name": owner.get("display_name"),
                "source_id": str(owner.get("user_id") or ""), "post_id": str(question.get("question_id")),
                "created_at": datetime.fromtimestamp(question.get("creation_date", 0), tz=UTC).isoformat() if question.get("creation_date") else None,
                "title": question.get("title", ""), "text": question.get("title", ""), "url": question.get("link"),
                "topic": query, "like_count": question.get("score", 0), "comment_count": question.get("answer_count", 0),
                "view_count": question.get("view_count", 0), "engagement_count": int(question.get("score", 0) or 0) + int(question.get("answer_count", 0) or 0),
            })
        return normalize_free_source_records(records, topic=query)

    @retry_api_call()
    def _request(self, params: dict) -> dict:
        response = requests.get(STACKEXCHANGE_SEARCH_URL, params=params, timeout=self.settings.request_timeout_seconds)
        if response.status_code >= 500:
            raise ConnectionError(f"Stack Exchange server error: {response.status_code}")
        response.raise_for_status()
        return response.json()
