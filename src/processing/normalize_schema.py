"""Normalize collector outputs into a unified platform schema."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.processing.clean_text import clean_text, extract_hashtags, extract_mentions, extract_urls

UNIFIED_COLUMNS = [
    "platform",
    "source_type",
    "source_name",
    "source_id",
    "post_id",
    "created_at",
    "text",
    "language",
    "url",
    "hashtags",
    "mentions",
    "shared_links",
    "engagement_count",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
    "impression_count",
    "country",
    "topic",
    "sentiment_label",
    "sentiment_score",
    "sentiment_confidence",
    "sentiment_subjectivity",
    "sentiment_backend",
    "sentiment_reason",
    "collected_at",
]


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO-8601."""
    return datetime.now(UTC).isoformat()


def to_utc(value: Any) -> pd.Timestamp | pd.NaT:
    """Convert a timestamp-like value to UTC."""
    if value in (None, ""):
        return pd.NaT
    return pd.to_datetime(value, utc=True, errors="coerce")


def normalize_x_posts(records: list[dict[str, Any]], topic: str | None = None) -> pd.DataFrame:
    """Normalize X API v2 tweet records."""
    rows: list[dict[str, Any]] = []
    collected_at = utc_now_iso()
    for record in records:
        metrics = record.get("public_metrics") or {}
        entities = record.get("entities") or {}
        hashtags = [h.get("tag", "").lower() for h in entities.get("hashtags", []) if h.get("tag")]
        mentions = [m.get("username", "").lower() for m in entities.get("mentions", []) if m.get("username")]
        links = [u.get("expanded_url") or u.get("url") for u in entities.get("urls", []) if u.get("expanded_url") or u.get("url")]
        text = record.get("text", "")
        like_count = int(metrics.get("like_count", 0) or 0)
        comment_count = int(metrics.get("reply_count", 0) or 0)
        share_count = int(metrics.get("retweet_count", 0) or 0) + int(metrics.get("quote_count", 0) or 0)
        rows.append(
            {
                "platform": "x",
                "source_type": "post",
                "source_name": record.get("author_id"),
                "source_id": record.get("author_id"),
                "post_id": str(record.get("id", "")),
                "created_at": to_utc(record.get("created_at")),
                "text": clean_text(text),
                "language": record.get("lang"),
                "url": f"https://x.com/i/web/status/{record.get('id')}" if record.get("id") else None,
                "hashtags": hashtags or extract_hashtags(text),
                "mentions": mentions or extract_mentions(text),
                "shared_links": links or extract_urls(text),
                "engagement_count": like_count + comment_count + share_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "share_count": share_count,
                "view_count": int(metrics.get("impression_count", 0) or 0),
                "impression_count": int(metrics.get("impression_count", 0) or 0),
                "country": None,
                "topic": topic,
                "sentiment_label": None,
                "sentiment_score": None,
                "sentiment_confidence": None,
                "sentiment_subjectivity": None,
                "sentiment_backend": None,
                "sentiment_reason": None,
                "collected_at": collected_at,
                "conversation_id": record.get("conversation_id"),
            }
        )
    return ensure_unified_columns(pd.DataFrame(rows))


def normalize_meta_ads(records: list[dict[str, Any]], topic: str | None = None) -> pd.DataFrame:
    """Normalize Meta Ad Library records."""
    rows: list[dict[str, Any]] = []
    collected_at = utc_now_iso()
    for record in records:
        text_parts = [
            record.get("ad_creative_bodies"),
            record.get("ad_creative_link_titles"),
            record.get("ad_creative_link_descriptions"),
        ]
        text = " ".join(_flatten_text(part) for part in text_parts if part)
        impressions = _range_midpoint(record.get("impressions"))
        spend = _range_midpoint(record.get("spend"))
        rows.append(
            {
                "platform": "meta",
                "source_type": "ad",
                "source_name": record.get("page_name"),
                "source_id": record.get("page_id"),
                "post_id": str(record.get("id") or record.get("ad_archive_id") or ""),
                "created_at": to_utc(record.get("ad_delivery_start_time")),
                "text": clean_text(text),
                "language": None,
                "url": record.get("ad_snapshot_url"),
                "hashtags": extract_hashtags(text),
                "mentions": extract_mentions(text),
                "shared_links": extract_urls(text),
                "engagement_count": impressions,
                "like_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "view_count": 0,
                "impression_count": impressions,
                "country": ",".join(record.get("targeted_or_reached_countries") or []),
                "topic": topic,
                "sentiment_label": None,
                "sentiment_score": None,
                "sentiment_confidence": None,
                "sentiment_subjectivity": None,
                "sentiment_backend": None,
                "sentiment_reason": None,
                "collected_at": collected_at,
                "estimated_spend": spend,
            }
        )
    return ensure_unified_columns(pd.DataFrame(rows))


def normalize_free_source_records(records: list[dict[str, Any]], topic: str | None = None) -> pd.DataFrame:
    """Normalize records from free public sources into the unified schema."""
    rows: list[dict[str, Any]] = []
    collected_at = utc_now_iso()
    for record in records:
        text = record.get("text") or record.get("title") or ""
        engagement_count = int(record.get("engagement_count", 0) or 0)
        rows.append(
            {
                "platform": record.get("platform"),
                "source_type": record.get("source_type"),
                "source_name": record.get("source_name"),
                "source_id": record.get("source_id"),
                "post_id": str(record.get("post_id") or record.get("id") or record.get("url") or ""),
                "created_at": to_utc(record.get("created_at")),
                "text": clean_text(text),
                "language": record.get("language"),
                "url": record.get("url"),
                "hashtags": extract_hashtags(text),
                "mentions": extract_mentions(text),
                "shared_links": extract_urls(text) or ([record["url"]] if record.get("url") else []),
                "engagement_count": engagement_count,
                "like_count": int(record.get("like_count", 0) or 0),
                "comment_count": int(record.get("comment_count", 0) or 0),
                "share_count": int(record.get("share_count", 0) or 0),
                "view_count": int(record.get("view_count", 0) or 0),
                "impression_count": int(record.get("impression_count", 0) or 0),
                "country": record.get("country"),
                "topic": record.get("topic") or topic,
                "sentiment_label": None,
                "sentiment_score": None,
                "sentiment_confidence": None,
                "sentiment_subjectivity": None,
                "sentiment_backend": None,
                "sentiment_reason": None,
                "collected_at": collected_at,
            }
        )
    return ensure_unified_columns(pd.DataFrame(rows))


def ensure_unified_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all unified columns exist in a stable order."""
    for column in UNIFIED_COLUMNS:
        if column not in df.columns:
            df[column] = None
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df[[*UNIFIED_COLUMNS, *[c for c in df.columns if c not in UNIFIED_COLUMNS]]]


def _flatten_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value)


def _range_midpoint(value: Any) -> int:
    if isinstance(value, dict):
        lower = int(value.get("lower_bound", 0) or 0)
        upper = int(value.get("upper_bound", lower) or lower)
        return int((lower + upper) / 2)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
