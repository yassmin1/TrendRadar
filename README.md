# Social Media Trend Tracker

A Python 3.11+ system for collecting public social media data from X API v2 and Meta Ad Library, normalizing it into one schema, detecting emerging trends, scoring sentiment, and exploring results in a Streamlit dashboard.

The supported sources are:

- X API v2 recent search for public keyword and hashtag search.
- Meta Ad Library API for public ads and campaign-related trend analysis.
- Optional Facebook Pages collector for approved Page Public Content Access or authorized page tokens.
- GDELT, Google News RSS, Reddit public search, Stack Exchange, arXiv, OpenAlex, Wikinews, RSS feeds, Wikipedia Pageviews, and Hacker News as free/low-cost trend signals.

The project does not collect private Facebook profiles, private groups, restricted user data, or private user content.

## Project Structure

```text
src/
  collectors/
    x_collector.py
    meta_ad_library_collector.py
    facebook_pages_collector.py
  processing/
    clean_text.py
    normalize_schema.py
    deduplicate.py
  analysis/
    trend_detection.py
    sentiment_analysis.py
    topic_modeling.py
    source_ranking.py
  dashboard/
  storage/
    database.py
    export.py
  utils/
    config.py
    logging_config.py
    retry.py
dashboard/
  app.py
tests/
main.py
.env.example
requirements.txt
```

The modern runnable path is `main.py` plus the package layout above.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` for live collection:

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
FREE_SOURCE_MAX_RECORDS=100
COLLECT_RSS=false
RSS_FEEDS=https://hnrss.org/frontpage,https://www.reddit.com/r/technology/.rss
COLLECT_WIKIPEDIA=true
WIKIPEDIA_ARTICLES=Artificial intelligence,Climate change,Election
COLLECT_HACKERNEWS=true
DEFAULT_COUNTRY=US
MAX_PAGES_PER_QUERY=3
SCHEDULE_MINUTES=60
DATABASE_URL=
TREND_WINDOW=6h
TREND_Z_THRESHOLD=1.0
ALERT_Z_THRESHOLD=2.0
ALERT_GROWTH_THRESHOLD=1.0
ALERT_MIN_POSTS=3
ALERT_WEBHOOK_URL=
SENTIMENT_BACKEND=auto
```

Keep `.env` out of git. All API keys and tokens must come from environment variables.

## Run Locally

Mock mode works without real API credentials:

```bash
python main.py
streamlit run dashboard/app.py
```

Live mode uses official APIs:

```bash
python main.py --live --query "AI" --query "#climate" --country US --max-pages 2
streamlit run dashboard/app.py
```

By default, X is cost-controlled with `X_COLLECTION_MODE=cheap_first`. In that mode the app uses cheaper sources first and does not spend X credits unless those sources produce alert-worthy topics. If Meta is disabled and no cheap live source is available, X is skipped and local fallback data is written.

Free/low-cost sources can run before X:

- `COLLECT_GDELT=true`
- `COLLECT_GOOGLE_NEWS=true` uses Google News' public RSS keyword search.
- `COLLECT_REDDIT=true` uses Reddit's public keyword search.
- `COLLECT_STACKEXCHANGE=true` searches recent Stack Overflow questions.
- `COLLECT_ARXIV=true` searches public arXiv papers.
- `COLLECT_OPENALEX=true` searches public OpenAlex scholarly works.
- `COLLECT_WIKINEWS=true` searches public Wikinews pages.
- `COLLECT_WIKIPEDIA=true`
- `COLLECT_HACKERNEWS=true`
- `COLLECT_RSS=true` with `RSS_FEEDS=...`

To force an X call for a run:

```bash
python main.py --live --force-x --query "AI" --max-pages 1
```

`FREE_SOURCE_MAX_RECORDS` controls the per-query limit for free search sources (default `100`). `LIVE_LOOKBACK_DAYS` keeps live trend analysis focused on recent records and drops future-dated or stale search results (default `90`). GDELT accepts up to `250` records per query. These sources do not require credentials, but individual providers may apply rate limits or temporarily reject a request; a failure in one source does not stop the rest of the collection.

To use X normally but with cache and daily budget controls:

```bash
python main.py --live --x-mode budgeted --query "AI" --max-pages 1
```

Cost controls:

- `X_COLLECTION_MODE=off`: never call X.
- `X_COLLECTION_MODE=cheap_first`: only call X after cheaper sources indicate an alert-worthy topic.
- `X_COLLECTION_MODE=budgeted`: call X for requested queries, using cache and daily budget limits.
- `X_CACHE_TTL_MINUTES=360`: reuse cached X responses for 6 hours.
- `X_DAILY_REQUEST_BUDGET=5`: allow at most 5 real X API requests per day.
- `ENABLE_API_HEALTH_ON_RUN=false`: avoids spending X search calls on every normal run.

Meta Ad Library collection is optional and disabled by default. Enable it for a run with:

```bash
python main.py --live --include-meta --query "AI" --country US --max-pages 2
```

Or enable it in `.env`:

```env
COLLECT_META=true
```

Run an API health check:

```bash
python main.py --health-check
python main.py --health-check --include-meta
```

Health checks may call provider endpoints. Run them intentionally, not on every schedule, when cost matters.

Run scheduled collection:

```bash
python main.py --schedule --schedule-minutes 60
```

Use PostgreSQL instead of local SQLite by setting `DATABASE_URL`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/trend_tracker
```

Outputs:

- `data/raw/x/*.json`: raw X API responses.
- `data/raw/meta_ads/*.json`: raw Meta Ad Library responses.
- `data/processed/unified_posts.csv`: normalized dashboard data.
- `data/processed/trends.csv`: detected trend windows.
- `data/processed/collection_runs.jsonl`: collection run status and API health checks.
- `data/trends.db`: local SQLite copy.

## API Access And Limits

X collection uses API v2 recent search and requests post ID, text, author ID, creation time, language, public metrics, entities, URLs, mentions, hashtags, and conversation ID when available. Pagination uses `next_token`, and 429 responses are handled with backoff.

Meta collection uses the public Ad Library API. It supports keyword search, country, active status, delivery dates, page ID where available, public ad text, impressions, spend ranges, page name, and page ID when returned by Meta.

Facebook Page collection is optional. It requires approved Page Public Content Access or an authorized page token. Do not use it for private profiles, private groups, or restricted content.

API availability, fields, and rate limits depend on your developer account, product approval, and current platform rules.

## Unified Schema

The normalized dataset includes:

```text
platform, source_type, source_name, source_id, post_id, created_at, text,
language, url, hashtags, mentions, shared_links, engagement_count,
like_count, comment_count, share_count, view_count, impression_count,
country, topic, sentiment_label, sentiment_score, collected_at
```

Timestamps are normalized to UTC. Duplicate records are removed by `platform` and `post_id`.

## Dashboard

The Streamlit dashboard includes:

- Keyword search.
- Platform and date filters.
- Topic group, sentiment, country, and source type filters.
- Configurable trend windows.
- Trend timeline.
- Trend lifecycle labels: new, emerging, rising, peak, declining, stable.
- Trend detail view.
- Top sources table.
- Top hashtags.
- Sentiment over time.
- Sentiment confidence and explanation fields.
- Most shared links.
- Possible trend origin table.
- Current and stored trend alerts.
- Data Science tab with topic clusters, forecasts, network influence, quality checks, and trend explanations.
- Raw data preview.
- CSV export.

Additional data science outputs:

- `data/processed/topic_clusters.csv`
- `data/processed/forecasts.csv`
- `data/processed/network_summary.csv`
- `data/processed/data_quality.csv`
- `data/processed/trend_explanations.csv`

Alerts are generated during pipeline runs and saved to `data/processed/alerts.jsonl`.
Set `ALERT_WEBHOOK_URL` to send Slack/Discord-compatible webhook notifications.

## Tests

```bash
pytest -q
```

Current unit tests cover text cleaning, schema normalization, deduplication, and trend detection.
