import pandas as pd

from src.analysis.alerts import generate_trend_alerts


def test_generate_trend_alerts_for_emerging_trend():
    trends = pd.DataFrame(
        [
            {
                "topic": "ai",
                "window_start": "2026-01-01T00:00:00Z",
                "post_count": 5,
                "engagement_count": 100,
                "z_score": 2.5,
                "growth_rate": 1.2,
                "lifecycle": "emerging",
            }
        ]
    )
    alerts = generate_trend_alerts(trends, min_posts=3)
    assert len(alerts) == 1
    assert alerts[0]["topic"] == "ai"
