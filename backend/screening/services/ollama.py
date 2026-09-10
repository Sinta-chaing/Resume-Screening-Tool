import requests
from django.conf import settings


def embed(text: str) -> list[float]:
    """Generate an embedding vector via Ollama.

    Uses /api/embed with truncate=True so long inputs are cut to the model's
    context window (mxbai-embed-large = 512 tokens) instead of erroring.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embed"
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": text,
        "truncate": True,
    }
    response = requests.post(url, json=payload, timeout=120)
    if not response.ok:
        raise RuntimeError(f"Ollama embeddings error: {response.text}")
    embeddings = response.json().get("embeddings") or []
    if not embeddings:
        raise RuntimeError("Ollama embeddings error: empty embedding response")
    return embeddings[0]


def chat(messages: list[dict]) -> str:
    """Generate a chat response via Ollama /api/generate."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    payload = {
        "model": settings.CHAT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    response = requests.post(url, json=payload, timeout=900)
    if not response.ok:
        raise RuntimeError(f"Ollama chat error: {response.text}")
    return response.json()["response"]