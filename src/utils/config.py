"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - used in minimal local envs
    BaseSettings = None
    Field = None
    SettingsConfigDict = None


if BaseSettings is not None:

    class Settings(BaseSettings):
        """Runtime settings loaded from environment variables and .env."""

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

        x_bearer_token: str | None = Field(default=None, alias="X_BEARER_TOKEN")
        meta_access_token: str | None = Field(default=None, alias="META_ACCESS_TOKEN")
        facebook_page_access_token: str | None = Field(default=None, alias="FACEBOOK_PAGE_ACCESS_TOKEN")
        facebook_page_ids: str | None = Field(default=None, alias="FACEBOOK_PAGE_IDS")
        database_url: str | None = Field(default=None, alias="DATABASE_URL")
        alert_webhook_url: str | None = Field(default=None, alias="ALERT_WEBHOOK_URL")

        data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
        default_country: str = Field(default="US", alias="DEFAULT_COUNTRY")
        request_timeout_seconds: int = Field(default=30, alias="REQUEST_TIMEOUT_SECONDS")
        max_pages_per_query: int = Field(default=3, alias="MAX_PAGES_PER_QUERY")
        api_mode: Literal["mock", "live"] = Field(default="mock", alias="API_MODE")
        collect_meta: bool = Field(default=False, alias="COLLECT_META")
        collect_gdelt: bool = Field(default=True, alias="COLLECT_GDELT")
        collect_google_news: bool = Field(default=True, alias="COLLECT_GOOGLE_NEWS")
        collect_reddit: bool = Field(default=True, alias="COLLECT_REDDIT")
        collect_stackexchange: bool = Field(default=True, alias="COLLECT_STACKEXCHANGE")
        collect_arxiv: bool = Field(default=True, alias="COLLECT_ARXIV")
        collect_openalex: bool = Field(default=True, alias="COLLECT_OPENALEX")
        collect_wikinews: bool = Field(default=True, alias="COLLECT_WIKINEWS")
        free_source_max_records: int = Field(default=100, alias="FREE_SOURCE_MAX_RECORDS")
        live_lookback_days: int = Field(default=90, alias="LIVE_LOOKBACK_DAYS")
        collect_rss: bool = Field(default=False, alias="COLLECT_RSS")
        rss_feeds: str | None = Field(default=None, alias="RSS_FEEDS")
        collect_wikipedia: bool = Field(default=True, alias="COLLECT_WIKIPEDIA")
        wikipedia_articles: str | None = Field(default=None, alias="WIKIPEDIA_ARTICLES")
        collect_hackernews: bool = Field(default=True, alias="COLLECT_HACKERNEWS")
        schedule_minutes: int = Field(default=60, alias="SCHEDULE_MINUTES")
        enable_api_health_on_run: bool = Field(default=False, alias="ENABLE_API_HEALTH_ON_RUN")
        x_collection_mode: Literal["off", "budgeted", "cheap_first"] = Field(default="cheap_first", alias="X_COLLECTION_MODE")
        x_cache_ttl_minutes: int = Field(default=360, alias="X_CACHE_TTL_MINUTES")
        x_daily_request_budget: int = Field(default=5, alias="X_DAILY_REQUEST_BUDGET")
        trend_window: str = Field(default="6h", alias="TREND_WINDOW")
        trend_z_threshold: float = Field(default=1.0, alias="TREND_Z_THRESHOLD")
        alert_z_threshold: float = Field(default=2.0, alias="ALERT_Z_THRESHOLD")
        alert_growth_threshold: float = Field(default=1.0, alias="ALERT_GROWTH_THRESHOLD")
        alert_min_posts: int = Field(default=3, alias="ALERT_MIN_POSTS")
        sentiment_backend: Literal["auto", "vader", "textblob", "lexicon"] = Field(default="auto", alias="SENTIMENT_BACKEND")

else:

    @dataclass
    class Settings:
        """Minimal fallback settings when pydantic-settings is not installed."""

        x_bearer_token: str | None = None
        meta_access_token: str | None = None
        facebook_page_access_token: str | None = None
        facebook_page_ids: str | None = None
        database_url: str | None = None
        alert_webhook_url: str | None = None
        data_dir: Path = Path("data")
        default_country: str = "US"
        request_timeout_seconds: int = 30
        max_pages_per_query: int = 3
        api_mode: Literal["mock", "live"] = "mock"
        collect_meta: bool = False
        collect_gdelt: bool = True
        collect_google_news: bool = True
        collect_reddit: bool = True
        collect_stackexchange: bool = True
        collect_arxiv: bool = True
        collect_openalex: bool = True
        collect_wikinews: bool = True
        free_source_max_records: int = 100
        live_lookback_days: int = 90
        collect_rss: bool = False
        rss_feeds: str | None = None
        collect_wikipedia: bool = True
        wikipedia_articles: str | None = None
        collect_hackernews: bool = True
        schedule_minutes: int = 60
        enable_api_health_on_run: bool = False
        x_collection_mode: Literal["off", "budgeted", "cheap_first"] = "cheap_first"
        x_cache_ttl_minutes: int = 360
        x_daily_request_budget: int = 5
        trend_window: str = "6h"
        trend_z_threshold: float = 1.0
        alert_z_threshold: float = 2.0
        alert_growth_threshold: float = 1.0
        alert_min_posts: int = 3
        sentiment_backend: Literal["auto", "vader", "textblob", "lexicon"] = "auto"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings after loading a local .env file when present."""
    load_dotenv()
    if BaseSettings is not None:
        return Settings()
    return Settings(
        x_bearer_token=os.getenv("X_BEARER_TOKEN"),
        meta_access_token=os.getenv("META_ACCESS_TOKEN"),
        facebook_page_access_token=os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN"),
        facebook_page_ids=os.getenv("FACEBOOK_PAGE_IDS"),
        database_url=os.getenv("DATABASE_URL"),
        alert_webhook_url=os.getenv("ALERT_WEBHOOK_URL"),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        default_country=os.getenv("DEFAULT_COUNTRY", "US"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        max_pages_per_query=int(os.getenv("MAX_PAGES_PER_QUERY", "3")),
        api_mode=os.getenv("API_MODE", "mock"),  # type: ignore[arg-type]
        collect_meta=os.getenv("COLLECT_META", "false").lower() in {"1", "true", "yes", "on"},
        collect_gdelt=os.getenv("COLLECT_GDELT", "true").lower() in {"1", "true", "yes", "on"},
        collect_google_news=os.getenv("COLLECT_GOOGLE_NEWS", "true").lower() in {"1", "true", "yes", "on"},
        collect_reddit=os.getenv("COLLECT_REDDIT", "true").lower() in {"1", "true", "yes", "on"},
        collect_stackexchange=os.getenv("COLLECT_STACKEXCHANGE", "true").lower() in {"1", "true", "yes", "on"},
        collect_arxiv=os.getenv("COLLECT_ARXIV", "true").lower() in {"1", "true", "yes", "on"},
        collect_openalex=os.getenv("COLLECT_OPENALEX", "true").lower() in {"1", "true", "yes", "on"},
        collect_wikinews=os.getenv("COLLECT_WIKINEWS", "true").lower() in {"1", "true", "yes", "on"},
        free_source_max_records=int(os.getenv("FREE_SOURCE_MAX_RECORDS", "100")),
        live_lookback_days=int(os.getenv("LIVE_LOOKBACK_DAYS", "90")),
        collect_rss=os.getenv("COLLECT_RSS", "false").lower() in {"1", "true", "yes", "on"},
        rss_feeds=os.getenv("RSS_FEEDS"),
        collect_wikipedia=os.getenv("COLLECT_WIKIPEDIA", "true").lower() in {"1", "true", "yes", "on"},
        wikipedia_articles=os.getenv("WIKIPEDIA_ARTICLES"),
        collect_hackernews=os.getenv("COLLECT_HACKERNEWS", "true").lower() in {"1", "true", "yes", "on"},
        schedule_minutes=int(os.getenv("SCHEDULE_MINUTES", "60")),
        enable_api_health_on_run=os.getenv("ENABLE_API_HEALTH_ON_RUN", "false").lower() in {"1", "true", "yes", "on"},
        x_collection_mode=os.getenv("X_COLLECTION_MODE", "cheap_first"),  # type: ignore[arg-type]
        x_cache_ttl_minutes=int(os.getenv("X_CACHE_TTL_MINUTES", "360")),
        x_daily_request_budget=int(os.getenv("X_DAILY_REQUEST_BUDGET", "5")),
        trend_window=os.getenv("TREND_WINDOW", "6h"),
        trend_z_threshold=float(os.getenv("TREND_Z_THRESHOLD", "1.0")),
        alert_z_threshold=float(os.getenv("ALERT_Z_THRESHOLD", "2.0")),
        alert_growth_threshold=float(os.getenv("ALERT_GROWTH_THRESHOLD", "1.0")),
        alert_min_posts=int(os.getenv("ALERT_MIN_POSTS", "3")),
        sentiment_backend=os.getenv("SENTIMENT_BACKEND", "auto"),  # type: ignore[arg-type]
    )
