"""Lightweight topic assignment helpers."""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


def infer_topics(df: pd.DataFrame, text_col: str = "text", top_n: int = 3) -> pd.DataFrame:
    """Fill missing topic values with frequent non-stopword terms from text."""
    result = df.copy()
    if "topic" not in result.columns:
        result["topic"] = None
    inferred: list[str] = []
    for text, existing in zip(result[text_col].fillna(""), result["topic"]):
        if existing:
            inferred.append(str(existing))
            continue
        words = [w.lower() for w in str(text).split() if len(w) > 2 and w.lower() not in ENGLISH_STOP_WORDS]
        top = [word for word, _ in Counter(words).most_common(top_n)]
        inferred.append(" ".join(top) if top else "uncategorized")
    result["topic"] = inferred
    return result


def add_topic_groups(df: pd.DataFrame, topic_col: str = "topic", text_col: str = "text") -> pd.DataFrame:
    """Group related topic labels with lightweight synonym and fuzzy matching."""
    result = df.copy()
    if result.empty:
        result["topic_group"] = []
        return result
    if topic_col not in result.columns:
        result = infer_topics(result, text_col=text_col)
    canonical_topics: list[str] = []
    topic_groups: list[str] = []
    for topic in result[topic_col].fillna("uncategorized").astype(str):
        normalized = _normalize_topic(topic)
        match = _find_existing_group(normalized, canonical_topics)
        if match is None:
            canonical_topics.append(normalized)
            topic_groups.append(normalized)
        else:
            topic_groups.append(match)
    result["topic_group"] = topic_groups
    return result


def _normalize_topic(topic: str) -> str:
    words = [word.lower().strip("#.,!?;:") for word in topic.split() if word.strip()]
    synonyms = {
        "chatgpt": "ai",
        "openai": "ai",
        "genai": "ai",
        "artificial": "ai",
        "intelligence": "ai",
        "climatechange": "climate",
        "globalwarming": "climate",
        "soccer": "sports",
        "football": "sports",
    }
    mapped = [synonyms.get(word, word) for word in words]
    unique = []
    for word in mapped:
        if word not in ENGLISH_STOP_WORDS and word not in unique:
            unique.append(word)
    return " ".join(unique[:3]) if unique else "uncategorized"


def _find_existing_group(topic: str, groups: list[str]) -> str | None:
    topic_terms = set(topic.split())
    for group in groups:
        group_terms = set(group.split())
        if topic_terms & group_terms:
            return group
        if SequenceMatcher(None, topic, group).ratio() >= 0.82:
            return group
    return None
