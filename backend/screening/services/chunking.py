MAX_CHUNKS = 500


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """Split text into chunks of approximately max_chars characters.

    ~800 chars keeps each chunk well inside the embedding model's 512-token
    context window (mxbai-embed-large) so no information is truncated away.
    """
    if not text or not text.strip():
        return []

    if not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError(f"Invalid max_chars: {max_chars}")

    cleaned = text.replace("\r", "").strip()

    if len(cleaned) > max_chars * MAX_CHUNKS:
        raise ValueError("Document too large to chunk safely")

    chunks = [
        cleaned[i : i + max_chars]
        for i in range(0, len(cleaned), max_chars)
    ]

    return chunks
