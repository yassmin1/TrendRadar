import pandas as pd

from src.analysis.sentiment_analysis import add_sentiment, score_sentiment


def test_score_sentiment_lexicon_positive():
    result = score_sentiment("This is a great strong win", backend="lexicon")
    assert result.label == "positive"
    assert result.score > 0
    assert result.confidence > 0
    assert result.backend == "lexicon"
    assert "positive_hits" in result.reason


def test_add_sentiment_adds_explainable_columns():
    df = pd.DataFrame({"text": ["great growth", "bad loss", "plain update"]})
    result = add_sentiment(df, backend="lexicon")
    for column in [
        "sentiment_label",
        "sentiment_score",
        "sentiment_confidence",
        "sentiment_subjectivity",
        "sentiment_backend",
        "sentiment_reason",
    ]:
        assert column in result.columns
    assert result.loc[0, "sentiment_label"] == "positive"
    assert result.loc[1, "sentiment_label"] == "negative"
