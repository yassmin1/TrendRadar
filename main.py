"""Run the social media trend tracking pipeline."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta

import pandas as pd
import requests

from src.analysis.sentiment_analysis import add_sentiment
from src.analysis.alerts import generate_trend_alerts, save_alerts, send_webhook_alerts
from src.analysis.topic_modeling import add_topic_groups, infer_topics
from src.analysis.topic_clustering import add_topic_clusters, summarize_topic_clusters
from src.analysis.trend_detection import detect_emerging_trends
from src.analysis.forecasting import forecast_trend_growth
from src.analysis.network_analysis import build_network_summary
from src.analysis.quality import score_data_quality
from src.analysis.explanations import explain_trends
from src.collectors.meta_ad_library_collector import MetaAdLibraryCollector
from src.collectors.x_collector import XCollector
from src.collectors.gdelt_collector import GDELTCollector
from src.collectors.rss_collector import RSSCollector
from src.collectors.wikipedia_collector import WikipediaPageviewsCollector
from src.collectors.hackernews_collector import HackerNewsCollector
from src.collectors.google_news_collector import GoogleNewsCollector
from src.collectors.reddit_collector import RedditCollector
from src.collectors.stackexchange_collector import StackExchangeCollector
from src.collectors.arxiv_collector import ArxivCollector
from src.collectors.openalex_collector import OpenAlexCollector
from src.collectors.wikinews_collector import WikinewsCollector
from src.processing.deduplicate import deduplicate_posts
from src.processing.normalize_schema import normalize_free_source_records
from src.storage.database import record_collection_run, save_dataframe_database, save_posts_database
from src.storage.export import save_csv
from src.utils.config import get_settings
from src.utils.cost_control import DailyBudgetExceeded
from src.utils.health import check_api_health
from src.utils.logging_config import configure_logging
from src.utils.retry import AccessDeniedError

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Collect and analyze public X and Meta trend data.")
    parser.add_argument("--query", action="append", help="Keyword or hashtag query. May be passed multiple times.")
    parser.add_argument("--live", action="store_true", help="Use live APIs instead of mock sample data.")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum API result pages per query.")
    parser.add_argument("--country", default=None, help="Meta Ad Library country code, for example US.")
    parser.add_argument("--include-meta", action="store_true", help="Include Meta Ad Library collection for this run.")
    parser.add_argument("--skip-meta", action="store_true", help="Skip Meta Ad Library collection even if COLLECT_META=true.")
    parser.add_argument("--health-check", action="store_true", help="Check configured API access and exit.")
    parser.add_argument("--schedule", action="store_true", help="Run collection repeatedly on SCHEDULE_MINUTES interval.")
    parser.add_argument("--schedule-minutes", type=int, default=None, help="Override SCHEDULE_MINUTES for --schedule.")
    parser.add_argument("--force-x", action="store_true", help="Call X even when X_COLLECTION_MODE=cheap_first.")
    parser.add_argument("--x-mode", choices=["off", "budgeted", "cheap_first"], default=None, help="Override X_COLLECTION_MODE for this run.")
    return parser.parse_args()


def main() -> None:
    """Run collection, normalization, analysis, and exports."""
    configure_logging()
    args = parse_args()
    settings = get_settings()
    if args.health_check:
        collect_meta = args.include_meta or (settings.collect_meta and not args.skip_meta)
        for check in check_api_health(settings, include_meta=collect_meta):
            LOGGER.info("%s: %s - %s", check["service"], check["status"], check["detail"])
        return
    if args.schedule:
        interval_minutes = args.schedule_minutes or settings.schedule_minutes
        LOGGER.info("Starting scheduled collection every %s minute(s). Press Ctrl+C to stop.", interval_minutes)
        while True:
            run_pipeline(args, settings)
            time.sleep(max(interval_minutes, 1) * 60)
    else:
        run_pipeline(args, settings)


def run_pipeline(args: argparse.Namespace, settings) -> None:
    """Run one collection and analysis cycle."""
    started_at = datetime.now(UTC).isoformat()
    queries = args.query or ["AI", "#climate", "election"]
    use_live = args.live or settings.api_mode == "live"
    collect_meta = args.include_meta or (settings.collect_meta and not args.skip_meta)
    x_mode = args.x_mode or settings.x_collection_mode
    health_checks = check_api_health(settings, include_meta=collect_meta) if use_live and settings.enable_api_health_on_run else []
    run_status = "success"
    run_message = ""

    frames: list[pd.DataFrame] = []
    try:
        if use_live:
            LOGGER.info("Running live API collection for queries: %s", queries)
            meta_collector = MetaAdLibraryCollector(settings) if collect_meta else None
            if not collect_meta:
                LOGGER.info("Meta Ad Library collection is disabled. Use --include-meta or COLLECT_META=true to enable it.")
            cheap_frames: list[pd.DataFrame] = []
            for query in queries:
                if settings.collect_gdelt:
                    try:
                        cheap_frames.append(GDELTCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping GDELT collection for %s: %s", query, exc)
                if settings.collect_google_news:
                    try:
                        cheap_frames.append(GoogleNewsCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping Google News collection for %s: %s", query, exc)
                if settings.collect_reddit:
                    try:
                        cheap_frames.append(RedditCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping Reddit collection for %s: %s", query, exc)
                if settings.collect_stackexchange:
                    try:
                        cheap_frames.append(StackExchangeCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping Stack Exchange collection for %s: %s", query, exc)
                if settings.collect_arxiv:
                    try:
                        cheap_frames.append(ArxivCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping arXiv collection for %s: %s", query, exc)
                if settings.collect_openalex:
                    try:
                        cheap_frames.append(OpenAlexCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping OpenAlex collection for %s: %s", query, exc)
                if settings.collect_wikinews:
                    try:
                        cheap_frames.append(WikinewsCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping Wikinews collection for %s: %s", query, exc)
                if settings.collect_hackernews:
                    try:
                        cheap_frames.append(HackerNewsCollector(settings).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping Hacker News collection for %s: %s", query, exc)
                if settings.collect_rss:
                    try:
                        cheap_frames.append(RSSCollector(_csv_values(settings.rss_feeds)).collect_dataframe(query=query))
                    except Exception as exc:
                        LOGGER.warning("Skipping RSS collection for %s: %s", query, exc)
                if meta_collector is not None:
                    try:
                        cheap_frames.append(meta_collector.collect_dataframe(keyword=query, country=args.country, max_pages=args.max_pages))
                    except AccessDeniedError as exc:
                        LOGGER.warning("Skipping Meta Ad Library collection for %s: %s", query, exc)
                    except requests.HTTPError as exc:
                        LOGGER.warning("Skipping Meta Ad Library collection for %s due to HTTP error: %s", query, exc)
            if settings.collect_wikipedia:
                try:
                    articles = _csv_values(settings.wikipedia_articles) or queries
                    cheap_frames.append(WikipediaPageviewsCollector(settings).collect_dataframe(articles=articles))
                except Exception as exc:
                    LOGGER.warning("Skipping Wikipedia Pageviews collection: %s", exc)
            frames.extend(cheap_frames)
            x_queries = _select_x_queries(queries, cheap_frames, settings, x_mode, args.force_x)
            if x_queries:
                LOGGER.info("X collection mode %s selected %s query/queries: %s", x_mode, len(x_queries), x_queries)
                x_collector = XCollector(settings)
                for query in x_queries:
                    try:
                        frames.append(x_collector.collect_dataframe(query=query, max_pages=args.max_pages))
                    except DailyBudgetExceeded as exc:
                        LOGGER.warning("Skipping remaining X collection: %s", exc)
                        break
                    except AccessDeniedError as exc:
                        LOGGER.warning("Skipping X collection for %s: %s", query, exc)
                    except requests.HTTPError as exc:
                        LOGGER.warning("Skipping X collection for %s due to HTTP error: %s", query, exc)
            else:
                LOGGER.info("X collection skipped by cost controls. Use --force-x or --x-mode budgeted to call X.")
        else:
            LOGGER.info("Running with mock data. Pass --live and set .env tokens for real API collection.")
            frames.append(build_mock_data())

        posts = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else pd.DataFrame()
        if posts.empty:
            run_status = "fallback_mock"
            run_message = "No live records collected; wrote mock dashboard data."
            LOGGER.warning("No live records collected. Writing mock dashboard data so the app can still run locally.")
            posts = build_mock_data()

        if use_live and not posts.empty:
            posts = _filter_live_time_range(posts, settings.live_lookback_days)
            if posts.empty:
                run_status = "fallback_mock"
                run_message = "No recent live records collected after timestamp filtering; wrote mock dashboard data."
                LOGGER.warning("No recent live records collected after timestamp filtering. Writing mock dashboard data.")
                posts = build_mock_data()

        posts = deduplicate_posts(posts)
        posts = infer_topics(posts)
        posts = add_topic_groups(posts)
        posts = add_sentiment(posts, backend=settings.sentiment_backend)
        posts = add_topic_clusters(posts)
        trends = detect_emerging_trends(
            posts,
            topic_col="topic_group",
            window=settings.trend_window,
            z_threshold=settings.trend_z_threshold,
        )
        if "topic_group" in trends.columns and "topic" not in trends.columns:
            trends = trends.rename(columns={"topic_group": "topic"})
        alerts = generate_trend_alerts(
            trends,
            z_threshold=settings.alert_z_threshold,
            growth_threshold=settings.alert_growth_threshold,
            min_posts=settings.alert_min_posts,
        )
        topic_clusters = summarize_topic_clusters(posts)
        forecasts = forecast_trend_growth(trends)
        network = build_network_summary(posts)
        quality = score_data_quality(posts)
        explanations = explain_trends(trends, posts, network, forecasts)
        alerts_path = save_alerts(alerts)
        send_webhook_alerts(alerts, settings.alert_webhook_url, timeout=settings.request_timeout_seconds)

        posts_path = save_csv(posts, "data/processed/unified_posts.csv")
        trends_path = save_csv(trends, "data/processed/trends.csv")
        clusters_path = save_csv(topic_clusters, "data/processed/topic_clusters.csv")
        forecasts_path = save_csv(forecasts, "data/processed/forecasts.csv")
        network_path = save_csv(network, "data/processed/network_summary.csv")
        quality_path = save_csv(quality, "data/processed/data_quality.csv")
        explanations_path = save_csv(explanations, "data/processed/trend_explanations.csv")
        storage_backend = save_posts_database(posts, settings.database_url)
        save_dataframe_database(trends, "trends", settings.database_url)
        save_dataframe_database(topic_clusters, "topic_clusters", settings.database_url)
        save_dataframe_database(forecasts, "forecasts", settings.database_url)
        save_dataframe_database(network, "network_summary", settings.database_url)
        save_dataframe_database(quality, "data_quality", settings.database_url)
        save_dataframe_database(explanations, "trend_explanations", settings.database_url)
        record_collection_run(
            status=run_status,
            started_at=started_at,
            source_mode="live" if use_live else "mock",
            posts_count=len(posts),
            trends_count=len(trends),
            message=run_message or (f"Generated {len(alerts)} alert(s)." if alerts else ""),
            health_checks=health_checks,
            database_url=settings.database_url,
        )

        LOGGER.info("Saved %s normalized posts to %s", len(posts), posts_path)
        LOGGER.info("Saved %s trend windows to %s", len(trends), trends_path)
        LOGGER.info("Saved %s cluster summaries to %s", len(topic_clusters), clusters_path)
        LOGGER.info("Saved %s forecasts to %s", len(forecasts), forecasts_path)
        LOGGER.info("Saved %s network nodes to %s", len(network), network_path)
        LOGGER.info("Saved %s quality checks to %s", len(quality), quality_path)
        LOGGER.info("Saved %s explanations to %s", len(explanations), explanations_path)
        LOGGER.info("Saved %s alert(s) to %s", len(alerts), alerts_path)
        LOGGER.info("Stored posts using %s backend", storage_backend)
        LOGGER.info("Run dashboard with: streamlit run dashboard/app.py")
    except Exception as exc:
        record_collection_run(
            status="failed",
            started_at=started_at,
            source_mode="live" if use_live else "mock",
            message=str(exc),
            health_checks=health_checks,
            database_url=settings.database_url,
        )
        raise


def _select_x_queries(
    queries: list[str],
    cheap_frames: list[pd.DataFrame],
    settings,
    x_mode: str,
    force_x: bool,
) -> list[str]:
    """Choose X queries with cost controls."""
    if force_x:
        return queries
    if x_mode == "off":
        return []
    if x_mode == "budgeted":
        return queries
    if x_mode != "cheap_first":
        return []
    cheap_posts = pd.concat([frame for frame in cheap_frames if not frame.empty], ignore_index=True) if cheap_frames else pd.DataFrame()
    if cheap_posts.empty:
        LOGGER.info("Cheap-source-first mode found no cheap source data; not spending X credits.")
        return []
    cheap_posts = deduplicate_posts(cheap_posts)
    cheap_posts = infer_topics(cheap_posts)
    cheap_posts = add_topic_groups(cheap_posts)
    cheap_posts = add_sentiment(cheap_posts, backend=settings.sentiment_backend)
    cheap_trends = detect_emerging_trends(
        cheap_posts,
        topic_col="topic_group",
        window=settings.trend_window,
        z_threshold=settings.trend_z_threshold,
    )
    if "topic_group" in cheap_trends.columns and "topic" not in cheap_trends.columns:
        cheap_trends = cheap_trends.rename(columns={"topic_group": "topic"})
    cheap_alerts = generate_trend_alerts(
        cheap_trends,
        z_threshold=settings.alert_z_threshold,
        growth_threshold=settings.alert_growth_threshold,
        min_posts=settings.alert_min_posts,
    )
    if not cheap_alerts:
        LOGGER.info("Cheap-source-first mode found no alert-worthy topics; not spending X credits.")
        return []
    alert_topics = {str(alert["topic"]).lower() for alert in cheap_alerts if alert.get("topic")}
    selected = [query for query in queries if any(term in query.lower() for term in alert_topics)]
    return selected or [str(next(iter(alert_topics)))]


def _csv_values(value: str | None) -> list[str]:
    """Parse comma-separated environment values."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _filter_live_time_range(posts: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    """Keep live analysis focused on recent, non-future records."""
    if "created_at" not in posts.columns or lookback_days <= 0:
        return posts
    cleaned = posts.copy()
    cleaned["created_at"] = pd.to_datetime(cleaned["created_at"], utc=True, errors="coerce")
    now = pd.Timestamp.now(tz=UTC)
    earliest = now - pd.Timedelta(days=lookback_days)
    latest = now + pd.Timedelta(days=1)
    before = len(cleaned)
    cleaned = cleaned[cleaned["created_at"].between(earliest, latest, inclusive="both")]
    dropped = before - len(cleaned)
    if dropped:
        LOGGER.info(
            "Dropped %s live record(s) outside %s-day analysis window or in the future.",
            dropped,
            lookback_days,
        )
    return cleaned.reset_index(drop=True)


def build_mock_data() -> pd.DataFrame:
    """Create a deterministic, analysis-ready seven-day dataset for mock mode."""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=7)
    topics = {
        "AI": {"tag": "AI", "phrase": "AI chip benchmark and safety policy", "sentiment": "promising", "counts": [3] * 24 + [5, 8, 14, 20]},
        "Climate change": {"tag": "Climate", "phrase": "climate resilience and clean-energy policy", "sentiment": "concerning", "counts": [7, 7, 6, 6] + [5] * 20 + [4, 3, 2, 2]},
        "Election": {"tag": "Election", "phrase": "election turnout and local campaign debate", "sentiment": "mixed", "counts": [2] * 24 + [3, 4, 8, 12]},
        "Cybersecurity": {"tag": "Cybersecurity", "phrase": "security patch and data breach response", "sentiment": "urgent", "counts": [2] * 22 + [3, 4, 7, 11, 15, 18]},
        "Renewable energy": {"tag": "CleanEnergy", "phrase": "solar storage and renewable energy investment", "sentiment": "positive", "counts": [4] * 28},
        "Sports": {"tag": "Sports", "phrase": "league match highlights and player performance", "sentiment": "exciting", "counts": [5, 4, 6, 5] * 7},
        "Gaming": {"tag": "Gaming", "phrase": "game launch update and creator reactions", "sentiment": "positive", "counts": [3] * 18 + [4] * 6 + [6, 8, 10, 9]},
        "Crypto": {"tag": "Crypto", "phrase": "crypto market volatility and regulation", "sentiment": "uncertain", "counts": [4, 5, 3, 4] * 7},
    }
    sources = [
        ("x", "post", "trendwatcher", "US"),
        ("reddit", "post", "r/technology", "US"),
        ("google_news", "news_article", "Industry Daily", "US"),
        ("hackernews", "story", "news_reader", "US"),
        ("stackexchange", "question", "Stack Overflow", "US"),
        ("arxiv", "paper", "arXiv", "US"),
        ("openalex", "work", "OpenAlex", "US"),
        ("wikinews", "news_page", "Wikinews", "US"),
        ("gdelt", "news_article", "Global News", "GB"),
        ("meta", "ad", "Public Campaign Page", "US"),
    ]
    records: list[dict[str, object]] = []
    for topic_index, (topic, details) in enumerate(topics.items()):
        for window_index, count in enumerate(details["counts"]):
            window_start = start + timedelta(hours=window_index * 6)
            for post_index in range(count):
                platform, source_type, source_name, country = sources[(topic_index + window_index + post_index) % len(sources)]
                engagement = 12 + topic_index * 5 + window_index * 2 + post_index * 7
                records.append(
                    {
                        "platform": platform,
                        "source_type": source_type,
                        "source_name": source_name,
                        "source_id": f"{platform}-{(topic_index + post_index) % 6}",
                        "post_id": f"mock-{topic_index}-{window_index}-{post_index}",
                        "created_at": (window_start + timedelta(minutes=(post_index * 17) % 350)).isoformat(),
                        "title": f"{topic}: {details['phrase']}",
                        "text": f"{details['phrase'].title()} is {details['sentiment']} in the latest discussion. #{details['tag']} @trenddesk",
                        "url": f"https://example.com/mock/{topic_index}/{window_index}/{post_index}",
                        "topic": topic,
                        "language": "en",
                        "country": country,
                        "like_count": engagement,
                        "comment_count": max(1, engagement // 6),
                        "share_count": max(0, engagement // 10),
                        "view_count": engagement * 20,
                        "engagement_count": engagement + max(1, engagement // 6) + max(0, engagement // 10),
                    }
                )
    return normalize_free_source_records(records)


if __name__ == "__main__":
    main()
