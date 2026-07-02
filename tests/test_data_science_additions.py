import pandas as pd

from src.analysis.explanations import explain_trends
from src.analysis.forecasting import forecast_trend_growth
from src.analysis.network_analysis import build_network_summary
from src.analysis.quality import score_data_quality
from src.analysis.topic_clustering import add_topic_clusters, summarize_topic_clusters


def sample_posts():
    return pd.DataFrame(
        [
            {
                "platform": "x",
                "post_id": "1",
                "created_at": "2026-01-01T00:00:00Z",
                "text": "AI chip benchmark is gaining",
                "topic": "AI",
                "topic_group": "ai",
                "hashtags": ["ai"],
                "mentions": [],
                "shared_links": ["https://example.com/a"],
                "engagement_count": 10,
                "sentiment_score": 0.2,
                "collected_at": "2026-01-01T00:01:00Z",
            },
            {
                "platform": "x",
                "post_id": "2",
                "created_at": "2026-01-01T01:00:00Z",
                "text": "AI benchmark report is gaining",
                "topic": "AI",
                "topic_group": "ai",
                "hashtags": ["ai"],
                "mentions": ["source"],
                "shared_links": ["https://example.com/a"],
                "engagement_count": 20,
                "sentiment_score": 0.3,
                "collected_at": "2026-01-01T01:01:00Z",
            },
        ]
    )


def test_topic_clustering_and_summary():
    clustered = add_topic_clusters(sample_posts())
    assert "topic_cluster" in clustered.columns
    summary = summarize_topic_clusters(clustered)
    assert not summary.empty


def test_forecast_network_quality_and_explanations():
    trends = pd.DataFrame(
        [
            {"topic": "ai", "window_start": "2026-01-01T00:00:00Z", "post_count": 1, "engagement_count": 10, "z_score": 0.0, "lifecycle": "new"},
            {"topic": "ai", "window_start": "2026-01-01T06:00:00Z", "post_count": 3, "engagement_count": 20, "z_score": 2.0, "lifecycle": "emerging"},
        ]
    )
    posts = sample_posts()
    forecasts = forecast_trend_growth(trends)
    network = build_network_summary(posts)
    quality = score_data_quality(posts)
    explanations = explain_trends(trends, posts, network, forecasts)
    assert forecasts.iloc[0]["trend_direction"] == "growing"
    assert not network.empty
    assert quality.iloc[0]["metric"] == "overall_quality_score"
    assert "forecast direction" in explanations.iloc[0]["explanation"]
