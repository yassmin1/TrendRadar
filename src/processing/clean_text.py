"""Text cleaning utilities."""

from __future__ import annotations

import re
from html import unescape

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: object) -> str:
    """Normalize social text while preserving hashtag and mention words."""
    if text is None:
        return ""
    value = unescape(str(text))
    value = URL_RE.sub(" ", value)
    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"[@#](\w+)", r"\1", value)
    value = re.sub(r"[^\w\s'/-]", " ", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def extract_hashtags(text: object) -> list[str]:
    """Extract lowercase hashtags without the leading #."""
    if text is None:
        return []
    value = unescape(str(text))
    return [tag.lower() for tag in re.findall(r"#(\w+)", value)]


def extract_mentions(text: object) -> list[str]:
    """Extract lowercase @mentions without the leading @."""
    if text is None:
        return []
    value = unescape(str(text))
    return [mention.lower() for mention in re.findall(r"@(\w+)", value)]


def extract_urls(text: object) -> list[str]:
    """Extract URLs from a text field."""
    if text is None:
        return []
    return URL_RE.findall(str(text))
