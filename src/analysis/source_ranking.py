"""Rank likely trend origins and amplifiers."""

from __future__ import annotations

from collections import Counter

import pandas as pd


def rank_trend_sources(df: pd.DataFrame, topic: str | None = None) -> pd.DataFrame:
    """Rank sources using timing, engagement, repeated URLs, hashtags, and phrases."""
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    if topic:
        topic_values = work["topic"]
        if isinstance(topic_values, pd.DataFrame):
            topic_values = topic_values.iloc[:, 0]
        work = work[topic_values.astype(str).str.lower() == topic.lower()]
    if work.empty:
        return pd.DataFrame()

    work["created_at"] = pd.to_datetime(work["created_at"], utc=True, errors="coerce")
    work["engagement_count"] = pd.to_numeric(work.get("engagement_count", 0), errors="coerce").fillna(0)
    first_time = work["created_at"].min()
    url_counts = Counter(_explode(work.get("shared_links", [])))
    hashtag_counts = Counter(_explode(work.get("hashtags", [])))

    rows = []
    for _, row in work.iterrows():
        minutes_after_first = max((row["created_at"] - first_time).total_seconds() / 60, 0) if pd.notna(row["created_at"]) else 999999
        early_score = 100 / (1 + minutes_after_first)
        engagement = float(row.get("engagement_count", 0) or 0)
        repeated_url_score = sum(url_counts[url] for url in _as_list(row.get("shared_links"))) * 2
        repeated_hashtag_score = sum(hashtag_counts[tag] for tag in _as_list(row.get("hashtags")))
        phrase_score = _phrase_repetition_score(str(row.get("text", "")), work["text"].astype(str).tolist())
        amplification_score = early_score + engagement * 0.1 + repeated_url_score + repeated_hashtag_score + phrase_score
        rows.append(
            {
                "platform": row.get("platform"),
                "source_name": row.get("source_name"),
                "source_id": row.get("source_id"),
                "post_id": row.get("post_id"),
                "created_at": row.get("created_at"),
                "engagement_count": engagement,
                "amplification_score": round(amplification_score, 3),
            }
        )
    return pd.DataFrame(rows).sort_values("amplification_score", ascending=False).reset_index(drop=True)


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if pd.isna(value):
        return []
    return [str(value)]


def _explode(series: object) -> list[str]:
    values: list[str] = []
    if not isinstance(series, pd.Series):
        return values
    for item in series:
        values.extend(_as_list(item))
    return values


def _phrase_repetition_score(text: str, all_texts: list[str]) -> int:
    phrases = [" ".join(text.lower().split()[i : i + 3]) for i in range(max(len(text.split()) - 2, 0))]
    if not phrases:
        return 0
    counts = Counter()
    corpus = " ".join(t.lower() for t in all_texts)
    for phrase in phrases:
        counts[phrase] = corpus.count(phrase)
    return sum(count for count in counts.values() if count > 1)
