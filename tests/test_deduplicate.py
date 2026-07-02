import pandas as pd

from src.processing.deduplicate import deduplicate_posts


def test_deduplicate_posts_keeps_latest_platform_post():
    df = pd.DataFrame(
        [
            {"platform": "x", "post_id": "1", "text": "old", "collected_at": "2026-01-01T00:00:00Z"},
            {"platform": "x", "post_id": "1", "text": "new", "collected_at": "2026-01-01T01:00:00Z"},
            {"platform": "meta", "post_id": "1", "text": "separate", "collected_at": "2026-01-01T00:00:00Z"},
        ]
    )
    result = deduplicate_posts(df)
    assert len(result) == 2
    assert result[result["platform"] == "x"].iloc[0]["text"] == "new"
