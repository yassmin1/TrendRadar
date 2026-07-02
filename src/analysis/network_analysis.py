"""Network-style influence summaries for hashtags, links, mentions, and sources."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


def build_network_summary(df: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    """Build a lightweight node influence table from repeated entities."""
    if df.empty:
        return pd.DataFrame(columns=["node_type", "node", "count", "engagement_count", "centrality_score"])
    counters: dict[tuple[str, str], Counter] = {
        ("hashtag", "hashtags"): Counter(),
        ("link", "shared_links"): Counter(),
        ("mention", "mentions"): Counter(),
    }
    engagement: Counter = Counter()
    co_occurrence: Counter = Counter()
    for _, row in df.iterrows():
        row_engagement = float(row.get("engagement_count", 0) or 0)
        row_nodes: list[tuple[str, str]] = []
        for (node_type, column), counter in counters.items():
            for value in _as_list(row.get(column)):
                key = (node_type, value)
                counter[value] += 1
                engagement[key] += row_engagement
                row_nodes.append(key)
        source = str(row.get("source_name") or row.get("source_id") or "")
        if source:
            key = ("source", source)
            engagement[key] += row_engagement
            row_nodes.append(key)
        for left, right in combinations(sorted(set(row_nodes)), 2):
            co_occurrence[left] += 1
            co_occurrence[right] += 1

    rows = []
    for (node_type, column), counter in counters.items():
        for node, count in counter.items():
            key = (node_type, node)
            rows.append(_node_row(node_type, node, count, engagement[key], co_occurrence[key]))
    source_counts = df["source_name"].fillna(df.get("source_id", "")).astype(str).value_counts() if "source_name" in df.columns else pd.Series(dtype=int)
    for node, count in source_counts.items():
        if node:
            key = ("source", node)
            rows.append(_node_row("source", node, int(count), engagement[key], co_occurrence[key]))
    return pd.DataFrame(rows).sort_values("centrality_score", ascending=False).head(top_n).reset_index(drop=True)


def _node_row(node_type: str, node: str, count: int, engagement_count: float, co_occurrence_count: int) -> dict[str, object]:
    return {
        "node_type": node_type,
        "node": node,
        "count": count,
        "engagement_count": int(engagement_count),
        "co_occurrence_count": co_occurrence_count,
        "centrality_score": round(count + co_occurrence_count * 0.5 + engagement_count * 0.01, 3),
    }


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value is None or pd.isna(value):
        return []
    return [str(value)]
