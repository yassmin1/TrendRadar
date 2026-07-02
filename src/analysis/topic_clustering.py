"""Lightweight topic clustering for similar social posts."""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def add_topic_clusters(df: pd.DataFrame, text_col: str = "text", max_clusters: int = 5) -> pd.DataFrame:
    """Assign TF-IDF/KMeans topic clusters without requiring heavy embedding models."""
    result = df.copy()
    if result.empty:
        result["topic_cluster"] = []
        result["topic_cluster_label"] = []
        return result
    texts = result[text_col].fillna("").astype(str).tolist()
    non_empty_count = sum(1 for text in texts if text.strip())
    if non_empty_count < 2:
        result["topic_cluster"] = 0
        result["topic_cluster_label"] = "uncategorized"
        return result

    vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_features=500, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(texts)
    cluster_count = max(1, min(max_clusters, non_empty_count, matrix.shape[0]))
    if cluster_count == 1:
        labels = [0] * len(texts)
    else:
        labels = KMeans(n_clusters=cluster_count, random_state=42, n_init="auto").fit_predict(matrix)
    result["topic_cluster"] = labels
    cluster_names = _cluster_names(matrix, labels, vectorizer.get_feature_names_out())
    result["topic_cluster_label"] = result["topic_cluster"].map(cluster_names)
    return result


def summarize_topic_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize cluster size, engagement, and sentiment."""
    if df.empty or "topic_cluster" not in df.columns:
        return pd.DataFrame(columns=["topic_cluster", "topic_cluster_label", "posts", "engagement_count", "avg_sentiment"])
    work = df.copy()
    work["engagement_count"] = pd.to_numeric(work.get("engagement_count", 0), errors="coerce").fillna(0)
    work["sentiment_score"] = pd.to_numeric(work.get("sentiment_score", 0), errors="coerce").fillna(0)
    return (
        work.groupby(["topic_cluster", "topic_cluster_label"], dropna=False)
        .agg(posts=("post_id", "count"), engagement_count=("engagement_count", "sum"), avg_sentiment=("sentiment_score", "mean"))
        .sort_values(["posts", "engagement_count"], ascending=False)
        .reset_index()
    )


def _cluster_names(matrix, labels, terms) -> dict[int, str]:
    names: dict[int, str] = {}
    for cluster in sorted(set(labels)):
        indexes = [index for index, label in enumerate(labels) if label == cluster]
        if not indexes:
            names[int(cluster)] = "uncategorized"
            continue
        centroid = matrix[indexes].mean(axis=0).A1
        top_terms = [terms[index] for index in centroid.argsort()[-3:][::-1] if centroid[index] > 0]
        names[int(cluster)] = ", ".join(top_terms) if top_terms else "uncategorized"
    return names
