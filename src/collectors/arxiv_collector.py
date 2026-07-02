"""arXiv public API keyword-search collector."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from src.processing.normalize_schema import normalize_free_source_records


class ArxivCollector:
    """Collect public arXiv papers matching a keyword query."""

    API_URL = "https://export.arxiv.org/api/query"

    def __init__(self, settings) -> None:
        self.settings = settings

    def collect_dataframe(self, query: str):
        max_records = min(max(self.settings.free_source_max_records, 1), 100)
        response = requests.get(
            self.API_URL,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_records,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            timeout=self.settings.request_timeout_seconds,
            headers={"User-Agent": "SocialMediaTrendTracker/1.0"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        records = []
        for entry in root.findall("atom:entry", ns):
            authors = [author.findtext("atom:name", default="", namespaces=ns) for author in entry.findall("atom:author", ns)]
            categories = [cat.attrib.get("term", "") for cat in entry.findall("atom:category", ns)]
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            url = entry.findtext("atom:id", default="", namespaces=ns)
            records.append(
                {
                    "platform": "arxiv",
                    "source_type": "paper",
                    "source_name": ", ".join(author for author in authors[:3] if author) or "arXiv",
                    "source_id": ",".join(category for category in categories if category),
                    "post_id": url,
                    "created_at": entry.findtext("atom:published", namespaces=ns),
                    "title": title,
                    "text": f"{title} {summary}",
                    "url": url,
                    "topic": query,
                    "language": "en",
                    "engagement_count": 0,
                }
            )
        return normalize_free_source_records(records, topic=query)
