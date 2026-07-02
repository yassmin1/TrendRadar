"""Database persistence for normalized social records and run metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def save_posts_sqlite(df: pd.DataFrame, db_path: str | Path = "data/trends.db", table: str = "posts") -> Path:
    """Persist posts to SQLite for local analysis."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = df.copy()
    for column in serializable.columns:
        serializable[column] = serializable[column].apply(
            lambda value: json.dumps(value) if isinstance(value, (list, dict)) else value
        )
    with sqlite3.connect(path) as conn:
        serializable.to_sql(table, conn, if_exists="replace", index=False)
    return path


def save_posts_database(df: pd.DataFrame, database_url: str | None, sqlite_path: str | Path = "data/trends.db") -> str:
    """Persist posts to PostgreSQL when DATABASE_URL is set, otherwise SQLite."""
    save_dataframe_database(df, "posts", database_url, sqlite_path)
    return "postgresql" if database_url else "sqlite"


def save_dataframe_database(
    df: pd.DataFrame,
    table: str,
    database_url: str | None,
    sqlite_path: str | Path = "data/trends.db",
) -> str:
    """Persist a dataframe to PostgreSQL when configured, otherwise SQLite."""
    if database_url:
        save_dataframe_postgres(df, database_url, table)
        return "postgresql"
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        _make_serializable(df).to_sql(table, conn, if_exists="replace", index=False)
    return "sqlite"


def save_dataframe_postgres(df: pd.DataFrame, database_url: str, table: str) -> None:
    """Persist a dataframe to PostgreSQL using SQLAlchemy if available."""
    try:
        from sqlalchemy import create_engine
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install sqlalchemy and psycopg2-binary to use DATABASE_URL/PostgreSQL storage.") from exc
    serializable = _make_serializable(df)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        serializable.to_sql(table, connection, if_exists="replace", index=False)


def load_posts_sqlite(db_path: str | Path = "data/trends.db", table: str = "posts") -> pd.DataFrame:
    """Load posts from SQLite when available."""
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame()
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)


def record_collection_run(
    status: str,
    started_at: str,
    ended_at: str | None = None,
    source_mode: str = "mock",
    posts_count: int = 0,
    trends_count: int = 0,
    message: str = "",
    health_checks: list[dict[str, Any]] | None = None,
    db_path: str | Path = "data/trends.db",
    database_url: str | None = None,
) -> None:
    """Persist collection-run metadata to JSONL and the configured database."""
    ended_at = ended_at or datetime.now(UTC).isoformat()
    row = {
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "source_mode": source_mode,
        "posts_count": posts_count,
        "trends_count": trends_count,
        "message": message,
        "health_checks": json.dumps(health_checks or []),
    }
    path = Path("data/processed/collection_runs.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")

    runs_df = load_collection_runs(path)
    if database_url:
        save_dataframe_postgres(runs_df, database_url, "collection_runs")
    else:
        db = Path(db_path)
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as conn:
            runs_df.to_sql("collection_runs", conn, if_exists="replace", index=False)


def load_collection_runs(path: str | Path = "data/processed/collection_runs.jsonl") -> pd.DataFrame:
    """Load collection-run metadata from JSONL."""
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    rows = [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DataFrame(rows)


def _make_serializable(df: pd.DataFrame) -> pd.DataFrame:
    serializable = df.copy()
    for column in serializable.columns:
        serializable[column] = serializable[column].apply(
            lambda value: json.dumps(value) if isinstance(value, (list, dict)) else value
        )
    return serializable
