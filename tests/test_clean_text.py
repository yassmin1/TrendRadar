from src.processing.clean_text import clean_text, extract_hashtags, extract_mentions, extract_urls


def test_clean_text_removes_urls_and_preserves_terms():
    text = "New #AI update from @OpenAI https://example.com\nLooks good!"
    assert clean_text(text) == "New AI update from OpenAI Looks good"
    assert extract_hashtags(text) == ["ai"]
    assert extract_mentions(text) == ["openai"]
    assert extract_urls(text) == ["https://example.com"]


def test_extract_hashtags_ignores_html_entity_numbers():
    text = "How to check if my app&#39;s issuer&#039;s card works with #AI"
    assert extract_hashtags(text) == ["ai"]
