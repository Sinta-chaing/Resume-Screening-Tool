import requests
from django.conf import settings


def embed(text: str) -> list[float]:
    """Generate an embedding vector via Ollama (single input)."""
    return embed_many([text])[0]


def embed_many(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts in one Ollama /api/embed call.

    Officially supported payload: ``input`` accepts either a string or an array
    of strings; ``embeddings`` in the response are returned in the same order.
    ``truncate=True`` cuts long inputs to the model's context window
    (mxbai-embed-large = 512 tokens) instead of erroring.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embed"
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
        "truncate": True,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    response = requests.post(url, json=payload, timeout=300)
    if not response.ok:
        raise RuntimeError(f"Ollama embeddings error: {response.text}")
    embeddings = response.json().get("embeddings") or []
    if not embeddings:
        raise RuntimeError("Ollama embeddings error: empty embedding response")
    return embeddings


def chat(messages: list[dict]) -> str:
    """Generate a chat response via Ollama /api/generate."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    payload = {
        "model": settings.CHAT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    response = requests.post(url, json=payload, timeout=900)
    if not response.ok:
        raise RuntimeError(f"Ollama chat error: {response.text}")
    return response.json()["response"]