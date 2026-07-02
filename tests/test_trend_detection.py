import pandas as pd

from src.analysis.trend_detection import detect_emerging_trends, normalize_trend_window


def test_detect_emerging_trends_flags_spike():
    base = pd.Timestamp("2026-01-01T00:00:00Z")
    rows = []
    for i in range(3):
        rows.append({"topic": "ai", "created_at": base + pd.Timedelta(hours=i * 6), "post_id": f"base-{i}", "engagement_count": 1})
    for i in range(4):
        rows.append({"topic": "ai", "created_at": base + pd.Timedelta(hours=18, minutes=i), "post_id": f"spike-{i}", "engagement_count": 10})
    result = detect_emerging_trends(pd.DataFrame(rows), z_threshold=1.0)
    assert result["is_emerging"].any()
    assert result.iloc[0]["topic"] == "ai"
    assert "lifecycle" in result.columns
    assert "growth_rate" in result.columns


def test_detect_emerging_trends_accepts_one_hour_window_aliases():
    base = pd.Timestamp("2026-01-01T00:00:00Z")
    rows = [
        {"topic": "ai", "created_at": base + pd.Timedelta(minutes=minute), "post_id": f"p-{minute}", "engagement_count": 1}
        for minute in range(0, 180, 30)
    ]
    df = pd.DataFrame(rows)
    counts = []
    for window in ["1", "1h", "1 hour"]:
        result = detect_emerging_trends(df, window=window)
        assert not result.empty
        counts.append(len(result))
    assert counts[0] == counts[1] == counts[2]


def test_normalize_trend_window_public_aliases():
    assert normalize_trend_window("1") == "1h"
    assert normalize_trend_window("1 hour") == "1h"
    assert normalize_trend_window("6 hours") == "6h"
    assert normalize_trend_window("24 hours") == "24h"
    assert normalize_trend_window("7 days") == "7d"
