"""Emerging trend detection."""

from __future__ import annotations

import pandas as pd


def detect_emerging_trends(
    df: pd.DataFrame,
    topic_col: str = "topic",
    timestamp_col: str = "created_at",
    window: str = "6h",
    z_threshold: float = 1.0,
    min_posts: int = 2,
) -> pd.DataFrame:
    """Detect topic spikes with rolling baseline z-score and lifecycle labels."""
    window = normalize_trend_window(window)
    if df.empty:
        return pd.DataFrame(columns=["topic", "window_start", "post_count", "engagement_count", "z_score", "is_emerging", "lifecycle"])
    required = {topic_col, timestamp_col}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing trend columns: {sorted(missing)}")

    work = df.copy()
    work[timestamp_col] = pd.to_datetime(work[timestamp_col], utc=True, errors="coerce")
    work = work.dropna(subset=[timestamp_col])
    work[topic_col] = work[topic_col].fillna("uncategorized").astype(str)
    if "engagement_count" not in work.columns:
        work["engagement_count"] = 0

    grouped = (
        work.set_index(timestamp_col)
        .groupby(topic_col)
        .resample(window)
        .agg(post_count=("post_id", "count"), engagement_count=("engagement_count", "sum"))
        .reset_index()
        .rename(columns={timestamp_col: "window_start"})
    )
    if grouped.empty:
        return grouped.assign(z_score=[], is_emerging=[])

    grouped = grouped.sort_values([topic_col, "window_start"])
    stats = grouped.groupby(topic_col)["post_count"]
    rolling_mean = stats.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    rolling_std = stats.transform(lambda s: s.shift(1).rolling(3, min_periods=1).std()).fillna(0)
    grouped["baseline_post_count"] = rolling_mean.fillna(0).round(3)
    grouped["z_score"] = ((grouped["post_count"] - grouped["baseline_post_count"]) / rolling_std.replace(0, 1)).round(3)
    grouped["previous_post_count"] = grouped.groupby(topic_col)["post_count"].shift(1).fillna(0)
    grouped["growth_rate"] = (
        (grouped["post_count"] - grouped["previous_post_count"]) / grouped["previous_post_count"].replace(0, 1)
    ).round(3)
    grouped["is_emerging"] = (grouped["post_count"] >= min_posts) & (grouped["z_score"] >= z_threshold)
    grouped["lifecycle"] = grouped.apply(lambda row: _classify_lifecycle(row, z_threshold, min_posts), axis=1)
    return grouped.sort_values(["is_emerging", "z_score", "engagement_count"], ascending=[False, False, False])


def normalize_trend_window(window: str) -> str:
    """Normalize user-facing trend-window values to pandas resample frequencies."""
    value = str(window or "6h").strip().lower()
    aliases = {
        "1": "1h",
        "1h": "1h",
        "1 hour": "1h",
        "1 hours": "1h",
        "hour": "1h",
        "6": "6h",
        "6h": "6h",
        "6 hour": "6h",
        "6 hours": "6h",
        "24": "24h",
        "24h": "24h",
        "24 hour": "24h",
        "24 hours": "24h",
        "1d": "24h",
        "1 day": "24h",
        "7": "7d",
        "7d": "7d",
        "7 day": "7d",
        "7 days": "7d",
        "week": "7d",
    }
    if value in aliases:
        return aliases[value]
    try:
        int(value)
    except ValueError:
        return value
    return f"{value}h"


def _classify_lifecycle(row: pd.Series, z_threshold: float, min_posts: int) -> str:
    """Classify a trend window into an easy-to-read lifecycle stage."""
    post_count = float(row.get("post_count", 0) or 0)
    previous = float(row.get("previous_post_count", 0) or 0)
    z_score = float(row.get("z_score", 0) or 0)
    growth = float(row.get("growth_rate", 0) or 0)
    if post_count < min_posts and previous == 0:
        return "new"
    if post_count >= min_posts and z_score >= z_threshold:
        return "emerging"
    if growth > 0.25:
        return "rising"
    if previous > 0 and post_count < previous:
        return "declining"
    if post_count >= previous and previous > 0:
        return "peak"
    return "stable"
