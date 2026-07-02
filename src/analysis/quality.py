"""Data quality scoring for collection outputs."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ["platform", "post_id", "created_at", "text", "topic", "collected_at"]


def score_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Return field-level and overall quality scores for a posts dataframe."""
    if df.empty:
        return pd.DataFrame(
            [{"metric": "overall_quality_score", "score": 0.0, "detail": "No records available."}]
        )
    rows = []
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            rows.append({"metric": f"missing_column_{column}", "score": 0.0, "detail": "Required column is absent."})
            continue
        completeness = float(df[column].notna().mean())
        if column == "text":
            completeness = float((df[column].fillna("").astype(str).str.len() > 0).mean())
        rows.append({"metric": f"{column}_completeness", "score": round(completeness, 4), "detail": f"{column} non-empty ratio"})
    duplicate_ratio = 0.0
    if {"platform", "post_id"}.issubset(df.columns):
        duplicate_ratio = float(df.duplicated(subset=["platform", "post_id"]).mean())
    rows.append({"metric": "duplicate_ratio", "score": round(1 - duplicate_ratio, 4), "detail": "1.0 means no duplicate platform/post_id pairs"})
    timestamp_validity = 0.0
    if "created_at" in df.columns:
        timestamp_validity = float(pd.to_datetime(df["created_at"], utc=True, errors="coerce").notna().mean())
    rows.append({"metric": "timestamp_validity", "score": round(timestamp_validity, 4), "detail": "created_at values parse as UTC timestamps"})
    overall = sum(row["score"] for row in rows if isinstance(row["score"], float)) / max(len(rows), 1)
    rows.insert(0, {"metric": "overall_quality_score", "score": round(overall, 4), "detail": "Average of completeness, duplicate, and timestamp checks"})
    return pd.DataFrame(rows)
