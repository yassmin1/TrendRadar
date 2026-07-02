# TrendRadar

TrendRadar is a Python and Streamlit application for spotting emerging public trends before they become obvious. It collects signals from public web, news, social, research, and community sources, normalizes them into one dataset, detects spikes, scores sentiment, forecasts momentum, and turns the results into an interactive dashboard.

Instead of only showing raw posts, TrendRadar helps answer the questions analysts actually ask:

- What topics are starting to move right now?
- Is the conversation growing, peaking, declining, or staying flat?
- Which hashtags, links, sources, and mentions are amplifying the trend?
- Is the public mood positive, negative, or neutral?
- Why does the system think this topic is trending?
- Which source may have started or accelerated the conversation?
- Is the data complete and reliable enough to trust?

![TrendRadar dashboard cover](app_coverpage.png)

## What It Does

TrendRadar turns scattered public signals into a readable trend intelligence workflow:

1. Collect public data from enabled sources.
2. Clean and normalize every record into one schema.
3. Deduplicate posts and standardize timestamps.
4. Extract hashtags, mentions, shared links, topics, and engagement signals.
5. Analyze sentiment with configurable backends.
6. Cluster similar posts and group related topics.
7. Detect emerging trends using rolling windows and spike scores.
8. Forecast whether each trend is likely to grow, flatten, or decline.
9. Rank possible origin sources and amplifiers.
10. Generate plain-language trend explanations and alerts.
11. Save results to CSV and SQLite or PostgreSQL.
12. Display everything in a Streamlit dashboard.

## Signal Sources

TrendRadar is designed to be useful even when paid API access is limited. It can run with mock data, free public sources, or live API sources.

Supported collectors include:

- X API v2 recent search for public keyword and hashtag monitoring.
- Meta Ad Library for public ads and campaign trend analysis.
- Facebook Pages when approved Page Public Content Access or authorized tokens are available.
- GDELT for global news signals.
- Google News RSS for public news search.
- Reddit public search.
- Stack Exchange questions.
- arXiv papers.
- OpenAlex scholarly works.
- Wikinews pages.
- Wikipedia Pageviews for public-interest spikes.
- Hacker News for technology and startup signals.
- RSS or Atom feeds.

The app does not collect private Facebook profiles, private groups, private messages, restricted user data, or private user content.

## Dashboard Highlights

The Streamlit dashboard is built for exploration, not just reporting. It includes:

- A front-page pipeline runner so users can collect data without typing commands.
- Collection status and API health visibility.
- Keyword, platform, date, topic, sentiment, country, and source filters.
- Trend timelines and lifecycle labels such as new, emerging, rising, peak, declining, and stable.
- Forecasts for next-window movement.
- Sentiment over time with confidence and explanation fields.
- Topic clusters and topic groups for cleaner analysis.
- Network-style influence summaries based on sources, hashtags, links, and mentions.
- Possible trend origin ranking.
- Current and stored trend alerts.
- Data quality checks.
- Raw data preview and CSV export.

## Cost-Aware API Design

X API credits can be limited or expensive, so TrendRadar includes budget controls.

Available X modes:

- `off`: never call X.
- `cheap_first`: use free or cheaper sources first, then call X only when a topic looks alert-worthy.
- `budgeted`: call X for requested queries while respecting cache and daily request limits.

Useful settings:

```env
X_COLLECTION_MODE=cheap_first
X_CACHE_TTL_MINUTES=360
X_DAILY_REQUEST_BUDGET=5
ENABLE_API_HEALTH_ON_RUN=false
```

This lets the app keep producing useful trend data while avoiding unnecessary paid API calls.

## Project Structure

```text
TrendRadar/
  main.py
  dashboard/
    app.py
  src/
    collectors/
    processing/
    analysis/
    storage/
    utils/
  tests/
  requirements.txt
```

Important modules:

- `main.py`: runs collection, processing, analysis, storage, alerts, and scheduling.
- `dashboard/app.py`: Streamlit interface for running and exploring the system.
- `src/collectors/`: source-specific public data collectors.
- `src/processing/`: text cleaning, schema normalization, and deduplication.
- `src/analysis/`: sentiment, clustering, forecasting, trend detection, explanations, alerts, and quality scoring.
- `src/storage/`: CSV and database output.
- `src/utils/`: configuration, retry logic, health checks, logging, and API cost controls.

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create your local environment file:

```bash
copy .env.example .env
```

Keep `.env` out of git. API keys and tokens should only be stored locally through environment variables.

## Quick Start

Run the full pipeline with mock or fallback data:

```bash
python main.py
```

Start the dashboard:

```bash
streamlit run dashboard/app.py
```

Then open:

```text
http://localhost:8501
```

## Run With Live Sources

Run live collection with cheap-first behavior:

```bash
python main.py --live --query "AI" --query "#climate" --country US --max-pages 2
```

Force an X API call for one run:

```bash
python main.py --live --force-x --query "AI" --max-pages 1
```

Use X with budget and cache controls:

```bash
python main.py --live --x-mode budgeted --query "AI" --max-pages 1
```

Disable X completely:

```bash
python main.py --live --x-mode off --query "AI"
```

Enable Meta Ad Library for a run:

```bash
python main.py --live --include-meta --query "AI" --country US --max-pages 2
```

Run scheduled collection:

```bash
python main.py --schedule --schedule-minutes 60
```

## Environment Configuration

Common `.env` settings:

```env
API_MODE=live

X_BEARER_TOKEN=your_x_api_v2_bearer_token
X_COLLECTION_MODE=cheap_first
X_CACHE_TTL_MINUTES=360
X_DAILY_REQUEST_BUDGET=5
ENABLE_API_HEALTH_ON_RUN=false

COLLECT_META=false
META_ACCESS_TOKEN=your_meta_graph_api_token

COLLECT_GDELT=true
COLLECT_GOOGLE_NEWS=true
COLLECT_REDDIT=true
COLLECT_STACKEXCHANGE=true
COLLECT_ARXIV=true
COLLECT_OPENALEX=true
COLLECT_WIKINEWS=true
COLLECT_WIKIPEDIA=true
COLLECT_HACKERNEWS=true
COLLECT_RSS=false
RSS_FEEDS=https://hnrss.org/frontpage,https://www.reddit.com/r/technology/.rss

DEFAULT_COUNTRY=US
MAX_PAGES_PER_QUERY=3
FREE_SOURCE_MAX_RECORDS=100
LIVE_LOOKBACK_DAYS=90
SCHEDULE_MINUTES=60

TREND_WINDOW=6h
TREND_Z_THRESHOLD=1.0
ALERT_Z_THRESHOLD=2.0
ALERT_GROWTH_THRESHOLD=1.0
ALERT_MIN_POSTS=3
ALERT_WEBHOOK_URL=

SENTIMENT_BACKEND=auto
DATABASE_URL=
```

Use PostgreSQL instead of local SQLite by setting:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/trend_tracker
```

## Outputs

TrendRadar writes local analysis outputs under `data/`:

```text
data/processed/unified_posts.csv
data/processed/trends.csv
data/processed/alerts.jsonl
data/processed/topic_clusters.csv
data/processed/forecasts.csv
data/processed/network_summary.csv
data/processed/data_quality.csv
data/processed/trend_explanations.csv
data/processed/collection_runs.jsonl
data/trends.db
```

Raw live API responses are stored under source-specific folders such as `data/raw/x/` and `data/raw/meta_ads/`.

## Unified Data Schema

Normalized records include:

```text
platform, source_type, source_name, source_id, post_id, created_at, text,
language, url, hashtags, mentions, shared_links, engagement_count,
like_count, comment_count, share_count, view_count, impression_count,
country, topic, topic_group, topic_cluster, topic_cluster_label,
sentiment_label, sentiment_score, sentiment_confidence,
sentiment_subjectivity, sentiment_backend, sentiment_reason, collected_at
```

Timestamps are normalized to UTC, and duplicate records are removed by source and post identity.

## Alerts

TrendRadar can generate alert records when a topic crosses configured spike and growth thresholds. Alerts are saved locally and can also be sent to Slack or Discord-compatible webhooks.

```env
ALERT_WEBHOOK_URL=https://your-webhook-url
ALERT_Z_THRESHOLD=2.0
ALERT_GROWTH_THRESHOLD=1.0
ALERT_MIN_POSTS=3
```

## API Health Checks

Run health checks intentionally, especially when API credits are limited:

```bash
python main.py --health-check
python main.py --health-check --include-meta
```

The app is designed to keep working even when a live provider fails. If no live records are collected, it can write fallback data so the dashboard remains usable locally.

## Tests

Run the test suite:

```bash
pytest -q
```

Tests cover cleaning, normalization, deduplication, sentiment, alerts, cost controls, trend detection, topic modeling, and free-source behavior.

## Built For

TrendRadar is useful for researchers, marketers, analysts, students, and developers who want a practical way to monitor public conversation. It combines collection, explainable analytics, forecasting, alerts, and a dashboard into one local-first trend intelligence app.
