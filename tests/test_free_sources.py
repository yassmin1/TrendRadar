import pandas as pd

from src.collectors.gdelt_collector import GDELTCollector
from src.collectors.hackernews_collector import HackerNewsCollector
from src.collectors.rss_collector import RSSCollector
from src.collectors.wikipedia_collector import WikipediaPageviewsCollector
from src.collectors.google_news_collector import GoogleNewsCollector
from src.collectors.reddit_collector import RedditCollector
from src.collectors.stackexchange_collector import StackExchangeCollector
from src.collectors.arxiv_collector import ArxivCollector
from src.collectors.openalex_collector import OpenAlexCollector
from src.collectors.wikinews_collector import WikinewsCollector
from src.processing.normalize_schema import normalize_free_source_records
from main import build_mock_data


def test_free_source_record_normalization():
    df = normalize_free_source_records(
        [
            {
                "platform": "gdelt",
                "source_type": "news_article",
                "source_name": "example.com",
                "post_id": "https://example.com/a",
                "created_at": "2026-01-01T00:00:00Z",
                "text": "AI trend is growing #AI",
                "url": "https://example.com/a",
                "topic": "AI",
                "engagement_count": 3,
            }
        ]
    )
    assert df.loc[0, "platform"] == "gdelt"
    assert df.loc[0, "hashtags"] == ["ai"]
    assert df.loc[0, "shared_links"]


def test_free_collectors_importable():
    assert GDELTCollector
    assert HackerNewsCollector
    assert RSSCollector
    assert WikipediaPageviewsCollector
    assert GoogleNewsCollector
    assert RedditCollector
    assert StackExchangeCollector
    assert ArxivCollector
    assert OpenAlexCollector
    assert WikinewsCollector


def test_mock_data_is_large_and_suitable_for_analysis():
    df = build_mock_data()
    assert len(df) >= 700
    assert df["platform"].nunique() >= 6
    assert df["topic"].nunique() >= 8
    assert df["created_at"].max() - df["created_at"].min() >= pd.Timedelta(days=6)
