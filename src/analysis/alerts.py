"""Trend alert generation and webhook delivery."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests


def generate_trend_alerts(
    trends: pd.DataFrame,
    z_threshold: float = 2.0,
    growth_threshold: float = 1.0,
    min_posts: int = 3,
) -> list[dict[str, Any]]:
    """Create alert payloads for trend windows that cross configured thresholds."""
    if trends.empty:
        return []
    alerts: list[dict[str, Any]] = []
    for _, row in trends.iterrows():
        post_count = int(row.get("post_count", 0) or 0)
        z_score = float(row.get("z_score", 0) or 0)
        growth_rate = float(row.get("growth_rate", 0) or 0)
        lifecycle = str(row.get("lifecycle", ""))
        if post_count >= min_posts and (z_score >= z_threshold or growth_rate >= growth_threshold or lifecycle == "emerging"):
            alerts.append(
                {
                    "created_at": datetime.now(UTC).isoformat(),
                    "topic": row.get("topic"),
                    "window_start": str(row.get("window_start")),
                    "post_count": post_count,
                    "engagement_count": int(row.get("engagement_count", 0) or 0),
                    "z_score": z_score,
                    "growth_rate": growth_rate,
                    "lifecycle": lifecycle,
                    "message": f"Trend alert: {row.get('topic')} is {lifecycle} with {post_count} posts.",
                }
            )
    return alerts


def save_alerts(alerts: list[dict[str, Any]], path: str | Path = "data/processed/alerts.jsonl") -> Path:
    """Append alerts to a JSONL file."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if alerts:
        with output.open("a", encoding="utf-8") as handle:
            for alert in alerts:
                handle.write(json.dumps(alert) + "\n")
    elif not output.exists():
        output.write_text("", encoding="utf-8")
    return output


def send_webhook_alerts(alerts: list[dict[str, Any]], webhook_url: str | None, timeout: int = 15) -> None:
    """Send alerts to a Slack/Discord-compatible webhook URL when configured."""
    if not alerts or not webhook_url:
        return
    for alert in alerts:
        response = requests.post(webhook_url, json={"text": alert["message"], "alert": alert}, timeout=timeout)
        response.raise_for_status()
