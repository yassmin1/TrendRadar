"""Streamlit dashboard for unified trend data."""

from __future__ import annotations

import ast
import html
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.alerts import generate_trend_alerts
from src.analysis.source_ranking import rank_trend_sources
from src.analysis.trend_detection import detect_emerging_trends, normalize_trend_window

POSTS_PATH = Path("data/processed/unified_posts.csv")
RUNS_PATH = Path("data/processed/collection_runs.jsonl")
ALERTS_PATH = Path("data/processed/alerts.jsonl")
CLUSTERS_PATH = Path("data/processed/topic_clusters.csv")
FORECASTS_PATH = Path("data/processed/forecasts.csv")
NETWORK_PATH = Path("data/processed/network_summary.csv")
QUALITY_PATH = Path("data/processed/data_quality.csv")
EXPLANATIONS_PATH = Path("data/processed/trend_explanations.csv")
SENTIMENT_ORDER = ["positive", "neutral", "negative"]
SENTIMENT_COLORS = {
    "positive": "#16a34a",
    "neutral": "#64748b",
    "negative": "#dc2626",
}

st.set_page_config(page_title="TrendRadar Internet Signal Monitoring System", layout="wide")


def apply_theme() -> None:
    """Apply light dashboard styling without changing Streamlit behavior."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .hero {
            padding: 1.35rem 1.5rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #111827 0%, #1d4ed8 55%, #06b6d4 100%);
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 14px 36px rgba(15, 23, 42, 0.18);
        }
        .hero h1 {
            margin: 0;
            font-size: 2.25rem;
            line-height: 1.1;
            color: #ffffff;
        }
        .hero p {
            margin: 0.45rem 0 0;
            color: rgba(255, 255, 255, 0.86);
            font-size: 1rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 0.85rem 1rem;
            box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stMetricLabel"] {
            color: #475569;
            font-weight: 650;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.55rem 1rem;
            background: #f1f5f9;
        }
        .stTabs [aria-selected="true"] {
            background: #dbeafe;
            color: #1d4ed8;
        }
        section[data-testid="stSidebar"] {
            background: #f8fafc;
        }
        h2, h3 {
            letter-spacing: -0.02em;
        }
        .insight-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.35rem 0 1.1rem;
        }
        .insight-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 18px;
            padding: 1rem;
            box-shadow: 0 8px 26px rgba(15, 23, 42, 0.07);
        }
        .insight-label {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 750;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .insight-value {
            color: #0f172a;
            font-size: 1.55rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }
        .insight-note {
            color: #475569;
            font-size: 0.88rem;
            margin-top: 0.35rem;
        }
        .narrative-card {
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            color: #1e3a8a;
            margin-bottom: 1rem;
        }
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.4rem 0 1.1rem;
        }
        .overview-card {
            border-radius: 20px;
            padding: 1rem;
            color: white;
            min-height: 112px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.13);
        }
        .overview-card:nth-child(1) { background: linear-gradient(135deg, #2563eb, #06b6d4); }
        .overview-card:nth-child(2) { background: linear-gradient(135deg, #7c3aed, #ec4899); }
        .overview-card:nth-child(3) { background: linear-gradient(135deg, #059669, #84cc16); }
        .overview-card:nth-child(4) { background: linear-gradient(135deg, #f97316, #ef4444); }
        .overview-label {
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            opacity: 0.82;
            text-transform: uppercase;
        }
        .overview-value {
            font-size: 1.85rem;
            font-weight: 850;
            line-height: 1.15;
            margin-top: 0.4rem;
        }
        .overview-note {
            font-size: 0.88rem;
            opacity: 0.9;
            margin-top: 0.35rem;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }
        .signal-row {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: center;
            padding: 0.62rem 0.75rem;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            background: #ffffff;
        }
        .signal-name {
            color: #0f172a;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .signal-count {
            background: #e0f2fe;
            color: #0369a1;
            border-radius: 999px;
            padding: 0.16rem 0.55rem;
            font-weight: 800;
            white-space: nowrap;
        }
        @media (max-width: 900px) {
            .overview-grid, .insight-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 560px) {
            .overview-grid, .insight-grid {
                grid-template-columns: 1fr;
            }
            .hero h1 {
                font-size: 1.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the dashboard hero."""
    st.markdown(
        """
        <div class="hero">
            <h1>TrendRadar Internet Signal Monitoring System</h1>
            <p>Monitor public web and social signals, detect spikes, compare sentiment, and identify likely source drivers.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_fig(fig):
    """Apply consistent chart styling."""
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=35, b=10),
        legend_title_text="",
        font=dict(family="Inter, Segoe UI, Arial", size=13),
    )
    return fig


def style_trend_timeline(fig):
    """Improve readability for the main trend timeline."""
    fig = style_fig(fig)
    fig.update_traces(mode="lines", line=dict(width=3))
    fig.update_layout(
        title=dict(text="Topic time series", x=0.02, xanchor="left", font=dict(size=20, color="#0f172a")),
        hovermode="x unified",
        xaxis_title="Time",
        yaxis_title="Post count",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e2e8f0", tickformat="%b %d\n%H:%M")
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0", rangemode="tozero")
    return fig


def signal_list(df: pd.DataFrame, name_col: str, count_col: str = "count", limit: int = 6) -> str:
    """Render compact ranked signal rows as HTML."""
    if df.empty or name_col not in df.columns:
        return '<div class="signal-row"><span class="signal-name">No signals found</span><span class="signal-count">0</span></div>'
    rows = []
    for _, row in df.head(limit).iterrows():
        name = html.escape(str(row.get(name_col, ""))[:80])
        count = int(row.get(count_col, 0) or 0)
        rows.append(f'<div class="signal-row"><span class="signal-name">{name}</span><span class="signal-count">{count:,}</span></div>')
    return '<div class="signal-list">' + "".join(rows) + "</div>"


apply_theme()
render_header()


@st.cache_data(ttl=300)
def load_posts() -> pd.DataFrame:
    """Load processed posts from local CSV."""
    if not POSTS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(POSTS_PATH)
    if "created_at" not in df.columns:
        df["created_at"] = pd.NaT
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    for column in ["hashtags", "mentions", "shared_links"]:
        if column in df.columns:
            df[column] = df[column].apply(parse_list)
        else:
            df[column] = [[] for _ in range(len(df))]
    for column in ["platform", "source_type", "source_name", "source_id", "post_id", "topic", "topic_group", "sentiment_label", "country", "text"]:
        if column not in df.columns:
            df[column] = ""
    for column in ["engagement_count", "sentiment_score", "sentiment_confidence"]:
        if column not in df.columns:
            df[column] = 0
    if "topic_group" not in df.columns and "topic" in df.columns:
        df["topic_group"] = df["topic"].fillna("uncategorized")
    df["topic_group"] = df["topic_group"].fillna("").astype(str)
    df.loc[df["topic_group"].str.strip() == "", "topic_group"] = df["topic"].fillna("uncategorized")
    df["topic_group"] = df["topic_group"].replace("", "uncategorized")
    return df


@st.cache_data(ttl=60)
def load_jsonl(path: Path) -> pd.DataFrame:
    """Load a JSONL file."""
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_csv(path: Path) -> pd.DataFrame:
    """Load an optional processed CSV."""
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame()


def parse_list(value: object) -> list[str]:
    """Parse list-like CSV values."""
    if isinstance(value, list):
        return value
    if pd.isna(value):
        return []
    try:
        parsed = ast.literal_eval(str(value))
        return parsed if isinstance(parsed, list) else []
    except (SyntaxError, ValueError):
        return []


def explode_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Count list values from a dataframe column."""
    if column not in df.columns or df.empty:
        return pd.DataFrame(columns=[column, "count"])
    exploded = df[[column]].explode(column)
    exploded = exploded[exploded[column].notna() & (exploded[column].astype(str) != "")]
    counts = exploded[column].value_counts().head(20)
    return pd.DataFrame({column: counts.index, "count": counts.values})


def options_for(df: pd.DataFrame, column: str) -> list[str]:
    """Return sorted non-empty options for a dataframe column."""
    if column not in df.columns:
        return []
    return sorted(str(value) for value in df[column].dropna().unique() if str(value).strip())


def sentiment_options(df: pd.DataFrame) -> list[str]:
    """Return sentiment labels in the product order, with unknown labels last."""
    values = options_for(df, "sentiment_label")
    ordered = [label for label in SENTIMENT_ORDER if label in values]
    extras = sorted(label for label in values if label not in SENTIMENT_ORDER)
    return ordered + extras


def filter_multiselect(df: pd.DataFrame, column: str, selected: list[str]) -> pd.DataFrame:
    """Apply a multiselect filter when values are selected."""
    if not selected or column not in df.columns:
        return df
    return df[df[column].fillna("").astype(str).isin(selected)]


def keyword_filter(df: pd.DataFrame, keyword: str, columns: list[str]) -> pd.DataFrame:
    """Filter across available text columns."""
    if not keyword:
        return df
    mask = pd.Series(False, index=df.index)
    for column in columns:
        if column in df.columns:
            mask = mask | df[column].fillna("").astype(str).str.contains(keyword, case=False, regex=False)
    return df[mask]


def valid_date_bounds(df: pd.DataFrame) -> tuple[object, object] | None:
    """Return valid min/max dates when timestamp data exists."""
    if "created_at" not in df.columns:
        return None
    dates = pd.to_datetime(df["created_at"], utc=True, errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.min().date(), dates.max().date()


def safe_numeric(series: object, default: float = 0.0) -> pd.Series:
    """Convert a dataframe column/series-like object to numeric values."""
    if isinstance(series, pd.Series):
        return pd.to_numeric(series, errors="coerce").fillna(default)
    return pd.Series(dtype=float)


def safe_mean(df: pd.DataFrame, column: str) -> float:
    """Return numeric mean with a stable zero fallback."""
    if column not in df.columns or df.empty:
        return 0.0
    value = safe_numeric(df[column]).mean()
    return 0.0 if pd.isna(value) else float(value)


def has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    """Check that all columns exist."""
    return all(column in df.columns for column in columns)


def render_status_panel() -> None:
    """Render collection status and API health."""
    runs = load_jsonl(RUNS_PATH)
    with st.expander("Collection and API Status", expanded=not runs.empty):
        if runs.empty:
            st.info("No collection run metadata found yet. Run `python main.py` to create it.")
            return
        latest = runs.iloc[-1]
        status_cols = st.columns(5)
        status_cols[0].metric("Last status", str(latest.get("status", "unknown")))
        status_cols[1].metric("Mode", str(latest.get("source_mode", "unknown")))
        status_cols[2].metric("Posts", int(latest.get("posts_count", 0) or 0))
        status_cols[3].metric("Trends", int(latest.get("trends_count", 0) or 0))
        status_cols[4].metric("Runs", len(runs))
        st.caption(f"Last run: {latest.get('started_at', '')} to {latest.get('ended_at', '')}")
        if latest.get("message"):
            st.warning(str(latest["message"]))
        try:
            health = json.loads(latest.get("health_checks", "[]"))
        except (TypeError, json.JSONDecodeError):
            health = []
        if health:
            st.dataframe(pd.DataFrame(health), use_container_width=True, hide_index=True)


def render_collection_runner() -> None:
    """Render a front-page form that runs the local collection pipeline."""
    with st.expander("Run collection pipeline", expanded=False):
        st.caption("Use this when you want to refresh the processed data behind the dashboard.")
        with st.form("collection_runner"):
            col1, col2, col3 = st.columns(3)
            with col1:
                run_mode = st.selectbox("Run mode", ["mock", "live"], index=0)
                query_text = st.text_area("Queries", value="AI\n#climate\nelection", height=110)
                max_pages = st.number_input("Max pages per query", min_value=1, max_value=10, value=1, step=1)
                country = st.text_input("Meta country", value="US")
            with col2:
                x_mode = st.selectbox("X mode", ["cheap_first", "off", "budgeted"], index=0)
                force_x = st.checkbox("Force X for this run", value=False)
                include_meta = st.checkbox("Include Meta Ad Library", value=False)
                st.caption("Public web sources")
                source_col1, source_col2 = st.columns(2)
                with source_col1:
                    collect_gdelt = st.checkbox("GDELT", value=True)
                    collect_google_news = st.checkbox("Google News", value=True)
                    collect_reddit = st.checkbox("Reddit", value=True)
                    collect_stackexchange = st.checkbox("Stack Exchange", value=True)
                    collect_hackernews = st.checkbox("Hacker News", value=True)
                with source_col2:
                    collect_arxiv = st.checkbox("arXiv", value=True)
                    collect_openalex = st.checkbox("OpenAlex", value=True)
                    collect_wikinews = st.checkbox("Wikinews", value=True)
                    collect_wikipedia = st.checkbox("Wikipedia Pageviews", value=True)
                    collect_rss = st.checkbox("RSS feeds", value=False)
            with col3:
                rss_feeds = st.text_area("RSS feeds, comma-separated", value="https://hnrss.org/frontpage", height=80)
                wikipedia_articles = st.text_area("Wikipedia articles, comma-separated", value="Artificial intelligence,Climate change,Election", height=80)
            live_lookback_days = st.number_input("Live lookback days", min_value=1, max_value=3650, value=90, step=1)
            sentiment_backend = st.selectbox("Sentiment backend", ["auto", "vader", "textblob", "lexicon"], index=0)
            pipeline_window_label = st.selectbox("Pipeline trend window", ["1 hour", "6 hours", "24 hours", "7 days"], index=1)
            trend_window = {"1 hour": "1h", "6 hours": "6h", "24 hours": "24h", "7 days": "7d"}[pipeline_window_label]
            trend_z = st.number_input("Trend z-threshold", min_value=0.1, max_value=10.0, value=1.0, step=0.1)

            run_submitted = st.form_submit_button("Run pipeline", use_container_width=True)

    if "run_submitted" not in locals():
        return
    if not run_submitted:
        return

    queries = [line.strip() for line in query_text.splitlines() if line.strip()]
    command = [sys.executable, "main.py"]
    if run_mode == "live":
        command.append("--live")
    for query in queries:
        command.extend(["--query", query])
    command.extend(["--max-pages", str(max_pages)])
    if country:
        command.extend(["--country", country])
    command.extend(["--x-mode", x_mode])
    if force_x:
        command.append("--force-x")
    if include_meta:
        command.append("--include-meta")

    env = os.environ.copy()
    env.update(
        {
            "API_MODE": run_mode,
            "COLLECT_GDELT": _bool_env(collect_gdelt),
            "COLLECT_GOOGLE_NEWS": _bool_env(collect_google_news),
            "COLLECT_REDDIT": _bool_env(collect_reddit),
            "COLLECT_STACKEXCHANGE": _bool_env(collect_stackexchange),
            "COLLECT_HACKERNEWS": _bool_env(collect_hackernews),
            "COLLECT_ARXIV": _bool_env(collect_arxiv),
            "COLLECT_OPENALEX": _bool_env(collect_openalex),
            "COLLECT_WIKINEWS": _bool_env(collect_wikinews),
            "COLLECT_WIKIPEDIA": _bool_env(collect_wikipedia),
            "COLLECT_RSS": _bool_env(collect_rss),
            "RSS_FEEDS": rss_feeds,
            "WIKIPEDIA_ARTICLES": wikipedia_articles,
            "LIVE_LOOKBACK_DAYS": str(live_lookback_days),
            "SENTIMENT_BACKEND": sentiment_backend,
            "TREND_WINDOW": trend_window,
            "TREND_Z_THRESHOLD": str(trend_z),
        }
    )

    with st.status("Running collection pipeline...", expanded=True) as status:
        st.code(" ".join(command), language="powershell")
        try:
            completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired as exc:
            status.update(label="Pipeline timed out", state="error")
            st.error("Pipeline timed out after 10 minutes.")
            if exc.stdout:
                st.text_area("Pipeline output", str(exc.stdout), height=220)
            if exc.stderr:
                st.text_area("Pipeline errors", str(exc.stderr), height=160)
            return
        if completed.stdout:
            st.text_area("Pipeline output", completed.stdout, height=260)
        if completed.stderr:
            st.text_area("Pipeline errors", completed.stderr, height=180)
        if completed.returncode == 0:
            st.cache_data.clear()
            status.update(label="Pipeline completed", state="complete")
            st.success("Collection finished. Refreshing dashboard data.")
            _rerun()
        else:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Pipeline failed with exit code {completed.returncode}.")
    return


def _bool_env(value: bool) -> str:
    return "true" if value else "false"


def _rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


render_collection_runner()
render_status_panel()

df = load_posts()
if df.empty:
    st.warning("No processed data found. Run `python main.py` for mock data or `python main.py --live --query \"your topic\"` for API data.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    st.caption("Filters control every chart and table below. Leave optional filters empty to include all values.")
    keyword = st.text_input("Keyword search", "", placeholder="Search text, topic, source...")
    trend_window_label = st.selectbox("Trend window", ["1 hour", "6 hours", "24 hours", "7 days"], index=1)
    trend_window = normalize_trend_window({"1 hour": "1h", "6 hours": "6h", "24 hours": "24h", "7 days": "7d"}[trend_window_label])
    z_threshold = st.slider("Spike sensitivity", min_value=0.5, max_value=4.0, value=1.0, step=0.25, help="Higher values require a stronger spike before a topic is marked emerging.")
    platform_options = options_for(df, "platform")
    platforms = st.multiselect("Platforms", platform_options, default=platform_options, help="At least one platform must be selected.")
    topics = st.multiselect("Topic groups", options_for(df, "topic_group"), default=[], help="Empty means all topic groups.")
    sentiments = st.multiselect("Sentiment labels", sentiment_options(df), default=[], help="Empty means all sentiment labels.")
    countries = st.multiselect("Countries", options_for(df, "country"), default=[], help="Empty means all countries.")
    source_types = st.multiselect("Source types", options_for(df, "source_type"), default=[], help="Empty means all source types.")
    bounds = valid_date_bounds(df)
    date_range = None
    if bounds:
        min_date, max_date = bounds
        date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        st.info("Date filter unavailable because no valid timestamps were found.")
    if st.button("Reset cached data", use_container_width=True):
        st.cache_data.clear()
        _rerun()

if platforms:
    filtered = df[df["platform"].fillna("").astype(str).isin(platforms)].copy()
else:
    filtered = df.iloc[0:0].copy()
    st.warning("Select at least one platform in the sidebar to display results.")
filtered = filter_multiselect(filtered, "topic_group", topics)
filtered = filter_multiselect(filtered, "sentiment_label", sentiments)
filtered = filter_multiselect(filtered, "country", countries)
filtered = filter_multiselect(filtered, "source_type", source_types)
filtered = keyword_filter(filtered, keyword, ["text", "topic", "topic_group", "source_name", "source_type", "platform"])
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start, end = pd.to_datetime(date_range[0], utc=True), pd.to_datetime(date_range[1], utc=True) + pd.Timedelta(days=1)
    filtered = filtered[(filtered["created_at"] >= start) & (filtered["created_at"] < end)]

trend_window = normalize_trend_window(trend_window)
trends = detect_emerging_trends(filtered, topic_col="topic_group", window=trend_window, z_threshold=z_threshold) if not filtered.empty else pd.DataFrame()
if "topic_group" in trends.columns and "topic" not in trends.columns:
    trends = trends.rename(columns={"topic_group": "topic"})
alerts = generate_trend_alerts(trends)
clusters = load_csv(CLUSTERS_PATH)
forecasts = load_csv(FORECASTS_PATH)
network_summary = load_csv(NETWORK_PATH)
quality = load_csv(QUALITY_PATH)
explanations = load_csv(EXPLANATIONS_PATH)

tabs = st.tabs(["Overview", "Trend Details", "Data Insights", "Sources", "Alerts", "Raw Data"])

with tabs[0]:
    top_topic = "None"
    top_topic_posts = 0
    if "topic_group" in filtered.columns and not filtered.empty:
        topic_counts = filtered["topic_group"].dropna().astype(str).value_counts()
        if not topic_counts.empty:
            top_topic = topic_counts.index[0]
            top_topic_posts = int(topic_counts.iloc[0])
    avg_sentiment = safe_mean(filtered, "sentiment_score")
    total_engagement = safe_numeric(filtered.get("engagement_count", pd.Series(dtype=float))).sum()

    st.markdown(
        f"""
        <div class="overview-grid">
            <div class="overview-card">
                <div class="overview-label">Collected posts</div>
                <div class="overview-value">{len(filtered):,}</div>
                <div class="overview-note">{filtered["platform"].nunique()} sources · {filtered["topic_group"].nunique() if "topic_group" in filtered else 0} topics</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Leading topic</div>
                <div class="overview-value">{html.escape(str(top_topic)[:24])}</div>
                <div class="overview-note">{top_topic_posts:,} matching posts in current filters</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Avg sentiment</div>
                <div class="overview-value">{avg_sentiment:.2f}</div>
                <div class="overview-note">Negative below 0 · positive above 0</div>
            </div>
            <div class="overview-card">
                <div class="overview-label">Engagement</div>
                <div class="overview-value">{total_engagement:,.0f}</div>
                <div class="overview-note">Combined public activity signals</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    timeline_col, mix_col = st.columns([2.15, 1])
    with timeline_col:
        st.subheader("Trend timeline")
        if not trends.empty:
            timeline_df = trends.copy()
            timeline_df["window_start"] = pd.to_datetime(timeline_df["window_start"], utc=True, errors="coerce")
            timeline_df = timeline_df.dropna(subset=["window_start"]).sort_values(["topic", "window_start"])
            fig = style_trend_timeline(
                px.line(
                    timeline_df,
                    x="window_start",
                    y="post_count",
                    color="topic",
                    hover_data={
                        "topic": True,
                        "lifecycle": True,
                        "post_count": ":,",
                        "z_score": ":.2f",
                        "growth_rate": ":.2f",
                        "engagement_count": ":,",
                    },
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for a trend timeline.")
    with mix_col:
        st.subheader("Composition")
        if not filtered.empty:
            source_mix = filtered["platform"].value_counts().reset_index()
            source_mix.columns = ["platform", "posts"]
            st.plotly_chart(
                style_fig(
                    px.pie(
                        source_mix,
                        names="platform",
                        values="posts",
                        hole=0.58,
                        color_discrete_sequence=px.colors.qualitative.Set3,
                    )
                ),
                use_container_width=True,
            )
        if not trends.empty:
            lifecycle_counts = trends["lifecycle"].value_counts().reset_index()
            lifecycle_counts.columns = ["lifecycle", "count"]
            lifecycle_fig = style_fig(
                px.bar(
                    lifecycle_counts,
                    x="count",
                    y="lifecycle",
                    orientation="h",
                    color="lifecycle",
                    labels={"count": "Number of time periods", "lifecycle": "Trend lifecycle"},
                    title=f"Lifecycle count by {trend_window_label.lower()} period",
                )
            )
            lifecycle_fig.update_layout(title_x=0.02)
            st.plotly_chart(lifecycle_fig, use_container_width=True)

    lower_left, lower_right = st.columns([1.25, 1])
    with lower_left:
        st.subheader("Sentiment flow")
        sentiment_df = filtered.dropna(subset=["created_at"]).copy()
        if not sentiment_df.empty:
            sentiment_df["window"] = sentiment_df["created_at"].dt.floor(normalize_trend_window(trend_window))
            sentiment_counts = sentiment_df.groupby(["window", "sentiment_label"]).size().reset_index(name="count")
            sentiment_counts["sentiment_label"] = pd.Categorical(sentiment_counts["sentiment_label"], categories=SENTIMENT_ORDER, ordered=True)
            sentiment_counts = sentiment_counts.sort_values(["window", "sentiment_label"])
            fig = style_fig(
                px.area(
                    sentiment_counts,
                    x="window",
                    y="count",
                    color="sentiment_label",
                    line_group="sentiment_label",
                    category_orders={"sentiment_label": SENTIMENT_ORDER},
                    color_discrete_map=SENTIMENT_COLORS,
                    labels={"window": "Time", "count": "Posts", "sentiment_label": "Sentiment"},
                )
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sentiment data available for current filters.")
    with lower_right:
        st.subheader("Top signals")
        signal_tabs = st.tabs(["Hashtags", "Links"])
        with signal_tabs[0]:
            st.markdown(signal_list(explode_counts(filtered, "hashtags"), "hashtags", limit=7), unsafe_allow_html=True)
        with signal_tabs[1]:
            st.markdown(signal_list(explode_counts(filtered, "shared_links"), "shared_links", limit=7), unsafe_allow_html=True)

        if {"sentiment_label", "sentiment_confidence"}.issubset(filtered.columns):
            sentiment_quality = filtered.groupby("sentiment_label", dropna=False)["sentiment_confidence"].mean().reset_index()
            sentiment_quality["sentiment_label"] = pd.Categorical(sentiment_quality["sentiment_label"], categories=SENTIMENT_ORDER, ordered=True)
            sentiment_quality = sentiment_quality.sort_values("sentiment_label")
            st.plotly_chart(
                style_fig(
                    px.bar(
                        sentiment_quality,
                        x="sentiment_label",
                        y="sentiment_confidence",
                        color="sentiment_label",
                        category_orders={"sentiment_label": SENTIMENT_ORDER},
                        color_discrete_map=SENTIMENT_COLORS,
                        labels={"sentiment_label": "Sentiment", "sentiment_confidence": "Confidence"},
                    )
                ),
                use_container_width=True,
            )

with tabs[1]:
    if trends.empty:
        st.info("No trend windows available for the current filters.")
    else:
        selected_topic = st.selectbox("Inspect topic", sorted(trends["topic"].dropna().astype(str).unique()))
        topic_trends = trends[trends["topic"].astype(str) == selected_topic].sort_values("window_start")
        topic_posts = filtered[filtered["topic_group"].astype(str) == selected_topic].sort_values("created_at")
        detail_cols = st.columns(4)
        detail_cols[0].metric("Latest lifecycle", str(topic_trends.iloc[-1]["lifecycle"]))
        detail_cols[1].metric("Max z-score", f"{topic_trends['z_score'].max():.2f}")
        detail_cols[2].metric("Total posts", len(topic_posts))
        detail_cols[3].metric("Total engagement", f"{safe_numeric(topic_posts.get('engagement_count', pd.Series(dtype=float))).sum():,.0f}")
        st.plotly_chart(style_fig(px.bar(topic_trends, x="window_start", y="post_count", color="lifecycle")), use_container_width=True)
        explanation_row = explanations[explanations["topic"].astype(str) == selected_topic].head(1) if has_columns(explanations, ["topic"]) and not explanations.empty else pd.DataFrame()
        if not explanation_row.empty:
            st.info(str(explanation_row.iloc[0]["explanation"]))
        forecast_row = forecasts[forecasts["topic"].astype(str) == selected_topic].head(1) if has_columns(forecasts, ["topic"]) and not forecasts.empty else pd.DataFrame()
        if not forecast_row.empty:
            st.dataframe(forecast_row, use_container_width=True, hide_index=True)
        st.dataframe(topic_posts[["created_at", "platform", "source_name", "text", "engagement_count", "sentiment_label"]].head(50), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Data Insights")
    st.caption("A compact readout of trend strength, forecast direction, influence signals, and data health.")

    quality_score = None
    if not quality.empty and {"metric", "score"}.issubset(quality.columns):
        overall = quality[quality["metric"] == "overall_quality_score"]
        if not overall.empty:
            quality_score = float(overall.iloc[0]["score"])
    quality_display = f"{quality_score:.2f}" if quality_score is not None else "N/A"

    strongest = trends.sort_values(["z_score", "post_count"], ascending=False).head(1) if not trends.empty else pd.DataFrame()
    strongest_topic = str(strongest.iloc[0]["topic"]) if not strongest.empty else "None"
    strongest_z = float(strongest.iloc[0]["z_score"]) if not strongest.empty else 0.0
    strongest_posts = int(strongest.iloc[0]["post_count"]) if not strongest.empty else 0

    top_forecast = forecasts.sort_values("forecast_next_post_count", ascending=False).head(1) if not forecasts.empty and "forecast_next_post_count" in forecasts else pd.DataFrame()
    forecast_topic = str(top_forecast.iloc[0]["topic"]) if not top_forecast.empty else "None"
    forecast_count = int(top_forecast.iloc[0]["forecast_next_post_count"]) if not top_forecast.empty else 0
    forecast_direction = str(top_forecast.iloc[0].get("trend_direction", "unknown")) if not top_forecast.empty else "unknown"

    top_node = network_summary.sort_values("centrality_score", ascending=False).head(1) if not network_summary.empty and "centrality_score" in network_summary else pd.DataFrame()
    node_name = str(top_node.iloc[0]["node"]) if not top_node.empty else "None"
    node_type = str(top_node.iloc[0].get("node_type", "signal")) if not top_node.empty else "signal"
    node_score = float(top_node.iloc[0]["centrality_score"]) if not top_node.empty else 0.0

    st.markdown(
        f"""
        <div class="insight-grid">
            <div class="insight-card">
                <div class="insight-label">Data health</div>
                <div class="insight-value">{quality_display}</div>
                <div class="insight-note">Completeness, duplicates, and timestamp validity.</div>
            </div>
            <div class="insight-card">
                <div class="insight-label">Strongest spike</div>
                <div class="insight-value">{html.escape(strongest_topic)}</div>
                <div class="insight-note">z-score {strongest_z:.2f} across {strongest_posts:,} posts.</div>
            </div>
            <div class="insight-card">
                <div class="insight-label">Top forecast</div>
                <div class="insight-value">{html.escape(forecast_topic)}</div>
                <div class="insight-note">{forecast_count:,} next-window posts, {html.escape(forecast_direction)}.</div>
            </div>
            <div class="insight-card">
                <div class="insight-label">Influence signal</div>
                <div class="insight-value">{html.escape(node_name[:28])}</div>
                <div class="insight-note">{html.escape(node_type)} · centrality {node_score:.2f}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not explanations.empty and "explanation" in explanations.columns:
        lead = html.escape(str(explanations.iloc[0]["explanation"]))
        st.markdown(f'<div class="narrative-card"><strong>Analyst summary:</strong> {lead}</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Topic clusters")
        if not clusters.empty and has_columns(clusters, ["posts", "topic_cluster_label", "avg_sentiment"]):
            cluster_plot = clusters.sort_values("posts", ascending=False).head(10)
            st.plotly_chart(
                style_fig(
                    px.bar(
                        cluster_plot,
                        x="posts",
                        y="topic_cluster_label",
                        color="avg_sentiment",
                        orientation="h",
                        color_continuous_scale="RdYlGn",
                        labels={"topic_cluster_label": "Cluster", "posts": "Posts", "avg_sentiment": "Avg sentiment"},
                    )
                ),
                use_container_width=True,
            )
        else:
            st.info("No topic cluster output found yet.")
    with right:
        st.subheader("Forecast outlook")
        if not forecasts.empty and has_columns(forecasts, ["topic", "forecast_next_post_count", "trend_direction"]):
            forecast_plot = forecasts.sort_values("forecast_next_post_count", ascending=False).head(10)
            st.plotly_chart(
                style_fig(
                    px.bar(
                        forecast_plot,
                        x="topic",
                        y="forecast_next_post_count",
                        color="trend_direction",
                        labels={"topic": "Topic", "forecast_next_post_count": "Forecast next-window posts"},
                    )
                ),
                use_container_width=True,
            )
        else:
            st.info("No forecast output found yet.")

    left, right = st.columns(2)
    with left:
        st.subheader("Network influence")
        if not network_summary.empty and has_columns(network_summary, ["count", "centrality_score", "engagement_count", "node_type", "node"]):
            influence_plot = network_summary.sort_values("centrality_score", ascending=False).head(12)
            st.plotly_chart(
                style_fig(
                    px.scatter(
                        influence_plot,
                        x="count",
                        y="centrality_score",
                        size="engagement_count",
                        color="node_type",
                        hover_name="node",
                        labels={"count": "Mentions / appearances", "centrality_score": "Influence score"},
                    )
                ),
                use_container_width=True,
            )
        else:
            st.info("No network summary output found yet.")
    with right:
        st.subheader("Data health checks")
        if not quality.empty and {"metric", "score", "detail"}.issubset(quality.columns):
            health_plot = quality[quality["metric"] != "overall_quality_score"].copy()
            health_plot["metric"] = health_plot["metric"].astype(str).str.replace("_", " ").str.title()
            st.plotly_chart(
                style_fig(
                    px.bar(
                        health_plot,
                        x="score",
                        y="metric",
                        orientation="h",
                        range_x=[0, 1],
                        labels={"score": "Score", "metric": "Check"},
                    )
                ),
                use_container_width=True,
            )
        elif not quality.empty:
            st.warning("Data quality output exists but does not match the expected schema. Run `python main.py` to regenerate it.")
        else:
            st.info("No data quality output found yet.")

    with st.expander("Detailed insight tables"):
        table_tabs = st.tabs(["Clusters", "Forecasts", "Network", "Quality", "Explanations"])
        with table_tabs[0]:
            st.dataframe(clusters, use_container_width=True, hide_index=True)
        with table_tabs[1]:
            st.dataframe(forecasts, use_container_width=True, hide_index=True)
        with table_tabs[2]:
            st.dataframe(network_summary, use_container_width=True, hide_index=True)
        with table_tabs[3]:
            st.dataframe(quality, use_container_width=True, hide_index=True)
        with table_tabs[4]:
            st.dataframe(explanations, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Top sources")
    source_summary = (
        filtered.groupby(["platform", "source_type", "source_name", "source_id"], dropna=False)
        .agg(posts=("post_id", "count"), engagement_count=("engagement_count", "sum"), first_seen=("created_at", "min"))
        .sort_values(["engagement_count", "posts"], ascending=False)
        .reset_index()
    )
    st.dataframe(source_summary.head(25), use_container_width=True, hide_index=True)

    st.subheader("Possible trend origin")
    origin_topic = st.selectbox("Origin topic", sorted(filtered["topic_group"].dropna().astype(str).unique())) if not filtered.empty else None
    origin_input = filtered.copy()
    if "topic_group" in origin_input.columns:
        origin_input["topic"] = origin_input["topic_group"]
    origin = rank_trend_sources(origin_input, origin_topic) if origin_topic else pd.DataFrame()
    st.dataframe(origin.head(25), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Alerts")
    stored_alerts = load_jsonl(ALERTS_PATH)
    current_alerts = pd.DataFrame(alerts)
    st.caption("Current alerts are computed from the active filters. Stored alerts are generated by pipeline runs.")
    if not current_alerts.empty:
        st.dataframe(current_alerts, use_container_width=True, hide_index=True)
    else:
        st.info("No current filtered trends cross the alert thresholds.")
    if not stored_alerts.empty:
        st.subheader("Stored alerts")
        st.dataframe(stored_alerts.tail(100), use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Raw data preview")
    st.dataframe(filtered.head(250), use_container_width=True, hide_index=True)
    sentiment_cols = [col for col in ["text", "sentiment_label", "sentiment_score", "sentiment_confidence", "sentiment_subjectivity", "sentiment_backend", "sentiment_reason"] if col in filtered.columns]
    if sentiment_cols:
        st.subheader("Sentiment explanations")
        st.dataframe(filtered[sentiment_cols].head(100), use_container_width=True, hide_index=True)
    st.download_button("Export filtered CSV", filtered.to_csv(index=False), file_name="trend_tracker_export.csv", mime="text/csv")
