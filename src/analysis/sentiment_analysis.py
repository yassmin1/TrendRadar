"""Configurable, explainable sentiment scoring."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import pandas as pd

try:
    from textblob import TextBlob
except ModuleNotFoundError:  # pragma: no cover - used in minimal envs
    TextBlob = None

try:
    from nltk.sentiment import SentimentIntensityAnalyzer
except ModuleNotFoundError:  # pragma: no cover - used in minimal envs
    SentimentIntensityAnalyzer = None

SentimentBackend = Literal["auto", "vader", "textblob", "lexicon"]


@dataclass(frozen=True)
class SentimentResult:
    """Detailed sentiment result for one text."""

    label: str
    score: float
    confidence: float
    subjectivity: float
    backend: str
    reason: str


def score_sentiment(text: object, backend: SentimentBackend = "auto") -> SentimentResult:
    """Score a text with the requested or best available sentiment backend."""
    value = "" if text is None else str(text).strip()
    if not value:
        return SentimentResult("neutral", 0.0, 0.0, 0.0, "none", "empty text")

    selected = _select_backend(backend)
    if selected == "vader":
        return _score_vader(value)
    if selected == "textblob":
        return _score_textblob(value)
    return _score_lexicon(value)


def add_sentiment(df: pd.DataFrame, text_col: str = "text", backend: SentimentBackend = "auto") -> pd.DataFrame:
    """Add explainable sentiment columns to a dataframe."""
    result = df.copy()
    if text_col not in result.columns:
        raise ValueError(f"Missing sentiment text column: {text_col}")
    scored = result[text_col].apply(lambda text: score_sentiment(text, backend=backend))
    result["sentiment_label"] = scored.apply(lambda item: item.label)
    result["sentiment_score"] = scored.apply(lambda item: item.score)
    result["sentiment_confidence"] = scored.apply(lambda item: item.confidence)
    result["sentiment_subjectivity"] = scored.apply(lambda item: item.subjectivity)
    result["sentiment_backend"] = scored.apply(lambda item: item.backend)
    result["sentiment_reason"] = scored.apply(lambda item: item.reason)
    return result


def _select_backend(requested: SentimentBackend) -> str:
    if requested == "vader" and _vader() is not None:
        return "vader"
    if requested == "textblob" and TextBlob is not None:
        return "textblob"
    if requested == "lexicon":
        return "lexicon"
    if requested == "auto":
        if _vader() is not None:
            return "vader"
        if TextBlob is not None:
            return "textblob"
    return "lexicon"


@lru_cache
def _vader():
    """Return a cached VADER analyzer when NLTK data is available."""
    if SentimentIntensityAnalyzer is None:
        return None
    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        return None


def _score_vader(text: str) -> SentimentResult:
    scores = _vader().polarity_scores(text)
    compound = float(scores["compound"])
    label = _label_from_score(compound)
    confidence = _confidence(compound)
    reason = f"VADER compound={compound:.3f}; pos={scores['pos']:.3f}; neu={scores['neu']:.3f}; neg={scores['neg']:.3f}"
    return SentimentResult(label, compound, confidence, 0.0, "vader", reason)


def _score_textblob(text: str) -> SentimentResult:
    blob = TextBlob(text)
    score = float(blob.sentiment.polarity)
    subjectivity = float(blob.sentiment.subjectivity)
    label = _label_from_score(score)
    return SentimentResult(
        label=label,
        score=round(score, 4),
        confidence=_confidence(score),
        subjectivity=round(subjectivity, 4),
        backend="textblob",
        reason=f"TextBlob polarity={score:.3f}; subjectivity={subjectivity:.3f}",
    )


def _score_lexicon(text: str) -> SentimentResult:
    words = [word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()]
    positive = {
        "amazing",
        "best",
        "excellent",
        "fast",
        "gain",
        "gaining",
        "good",
        "great",
        "growth",
        "improve",
        "love",
        "positive",
        "strong",
        "win",
    }
    negative = {
        "bad",
        "crash",
        "decline",
        "fail",
        "fear",
        "hate",
        "loss",
        "negative",
        "risk",
        "slow",
        "weak",
        "worse",
    }
    pos_hits = sum(1 for word in words if word in positive)
    neg_hits = sum(1 for word in words if word in negative)
    score = max(min((pos_hits - neg_hits) / max(len(words), 1), 1.0), -1.0)
    label = _label_from_score(score)
    reason = f"Lexicon positive_hits={pos_hits}; negative_hits={neg_hits}; tokens={len(words)}"
    return SentimentResult(label, round(score, 4), _confidence(score), 0.0, "lexicon", reason)


def _label_from_score(score: float) -> str:
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


def _confidence(score: float) -> float:
    return round(min(abs(score) * 2, 1.0), 4)
