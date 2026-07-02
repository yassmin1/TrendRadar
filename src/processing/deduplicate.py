"""Record de-duplication."""

from __future__ import annotations

import pandas as pd


def deduplicate_posts(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate platform/post_id pairs, keeping the latest collected copy."""
    if df.empty:
        return df.copy()
    required = {"platform", "post_id"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Cannot deduplicate without columns: {sorted(missing)}")
    ordered = df.sort_values("collected_at") if "collected_at" in df.columns else df
    return ordered.drop_duplicates(subset=["platform", "post_id"], keep="last").reset_index(drop=True)
