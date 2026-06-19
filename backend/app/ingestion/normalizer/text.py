import re


def strip_html(html: str) -> str:
    """Strip HTML tags and decode common entities from a string, returning plain text."""
    if not html:
        return ""
    clean = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }
    for ent, char in entities.items():
        clean = clean.replace(ent, char)
    return re.sub(r"\s+", " ", clean).strip()


def make_snippet(text: str, max_chars: int = 500) -> str:
    """Truncate plain text to max_chars at a word boundary and append an ellipsis if needed."""
    plain = strip_html(text)
    if len(plain) <= max_chars:
        return plain
    truncated = plain[:max_chars]
    last_space = truncated.rfind(" ")
    return (truncated[:last_space] if last_space > 0 else truncated) + "..."
