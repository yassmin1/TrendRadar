"""Simple trend forecasting utilities."""

from __future__ import annotations

import pandas as pd


def forecast_trend_growth(trends: pd.DataFrame) -> pd.DataFrame:
    """Forecast next-window post count from recent slope per topic."""
    if trends.empty:
        return pd.DataFrame(columns=["topic", "latest_window", "latest_post_count", "forecast_next_post_count", "trend_direction"])
    work = trends.copy()
    work["window_start"] = pd.to_datetime(work["window_start"], utc=True, errors="coerce")
    rows = []
    for topic, group in work.dropna(subset=["window_start"]).sort_values("window_start").groupby("topic"):
        recent = group.tail(3)
        latest = recent.iloc[-1]
        if len(recent) >= 2:
            slope = (recent["post_count"].iloc[-1] - recent["post_count"].iloc[0]) / (len(recent) - 1)
        else:
            slope = 0
        forecast = max(int(round(float(latest["post_count"]) + slope)), 0)
        if slope > 0.25:
            direction = "growing"
        elif slope < -0.25:
            direction = "declining"
        else:
            direction = "flat"
        rows.append(
            {
                "topic": topic,
                "latest_window": latest["window_start"],
                "latest_post_count": int(latest["post_count"]),
                "forecast_next_post_count": forecast,
                "trend_direction": direction,
                "slope": round(float(slope), 3),
            }
        )
    return pd.DataFrame(rows).sort_values(["forecast_next_post_count", "slope"], ascending=False)
