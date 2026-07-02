from src.processing.normalize_schema import UNIFIED_COLUMNS, normalize_x_posts


def test_normalize_x_posts_unified_columns_and_metrics():
    df = normalize_x_posts(
        [
            {
                "id": "1",
                "text": "Hello #Trend",
                "author_id": "42",
                "created_at": "2026-01-01T00:00:00Z",
                "lang": "en",
                "public_metrics": {"like_count": 2, "reply_count": 1, "retweet_count": 3, "quote_count": 1, "impression_count": 10},
                "entities": {"hashtags": [{"tag": "Trend"}]},
            }
        ],
        topic="Trend",
    )
    assert list(df.columns[: len(UNIFIED_COLUMNS)]) == UNIFIED_COLUMNS
    assert df.loc[0, "platform"] == "x"
    assert df.loc[0, "engagement_count"] == 7
    assert df.loc[0, "hashtags"] == ["trend"]
