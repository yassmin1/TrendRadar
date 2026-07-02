import pandas as pd

from src.analysis.topic_modeling import add_topic_groups


def test_add_topic_groups_groups_related_terms():
    df = pd.DataFrame(
        {
            "topic": ["AI", "ChatGPT", "football", "soccer"],
            "text": ["", "", "", ""],
        }
    )
    result = add_topic_groups(df)
    assert result.loc[0, "topic_group"] == result.loc[1, "topic_group"]
    assert result.loc[2, "topic_group"] == result.loc[3, "topic_group"]
