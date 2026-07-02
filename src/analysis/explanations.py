"""Generate explainable trend summaries."""

from __future__ import annotations

import pandas as pd


def explain_trends(trends: pd.DataFrame, posts: pd.DataFrame, network: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    """Create concise explanations for each topic trend."""
    if trends.empty:
        return pd.DataFrame(columns=["topic", "explanation"])
    rows = []
    latest = trends.sort_values("window_start").groupby("topic", as_index=False).tail(1)
    for _, trend in latest.iterrows():
        topic = str(trend["topic"])
        topic_posts = posts[posts.get("topic_group", posts.get("topic", "")).astype(str) == topic] if not posts.empty else pd.DataFrame()
        top_hashtags = _top_values(topic_posts, "hashtags")
        top_links = _top_values(topic_posts, "shared_links")
        top_network = network.head(3)["node"].tolist() if not network.empty else []
        forecast_row = forecasts[forecasts["topic"].astype(str) == topic].head(1) if not forecasts.empty else pd.DataFrame()
        direction = forecast_row.iloc[0]["trend_direction"] if not forecast_row.empty else "unknown"
        explanation = (
            f"{topic} is {trend.get('lifecycle', 'active')} with {int(trend.get('post_count', 0))} posts "
            f"in the latest window, z-score {float(trend.get('z_score', 0)):.2f}, and forecast direction {direction}. "
            f"Repeated hashtags: {', '.join(top_hashtags) or 'none'}. "
            f"Repeated links: {', '.join(top_links) or 'none'}. "
            f"High-centrality entities: {', '.join(map(str, top_network)) or 'none'}."
        )
        rows.append({"topic": topic, "window_start": trend.get("window_start"), "explanation": explanation})
    return pd.DataFrame(rows)


def _top_values(df: pd.DataFrame, column: str, top_n: int = 3) -> list[str]:
    if df.empty or column not in df.columns:
        return []
    values = df[[column]].explode(column)[column].dropna().astype(str)
    return values[values != ""].value_counts().head(top_n).index.tolist()
