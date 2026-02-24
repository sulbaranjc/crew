"""Generación de embeddings usando nomic-embed-text vía Ollama."""

import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def get_embedding(texto: str) -> list[float]:
    """Convierte un texto en su vector de embeddings (768 dimensiones)."""
    resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "prompt": texto})
    resp.raise_for_status()
    return resp.json()["embedding"]
