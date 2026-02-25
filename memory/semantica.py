"""Memoria semántica — hechos clave del usuario (PostgreSQL + pgvector)."""

from datetime import datetime
from .db import get_conn
from .embeddings import get_embedding

AGENTE = "chatty"
TOP_K = 5

_cache_hay_hechos: bool | None = None


def guardar_hecho(hecho: str) -> None:
    """Guarda un hecho junto con su vector de embeddings."""
    global _cache_hay_hechos
    embedding = get_embedding(hecho)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hechos (agente, hecho, embedding, timestamp) VALUES (%s, %s, %s, %s)",
                (AGENTE, hecho, str(embedding), datetime.now())
            )
        conn.commit()
        _cache_hay_hechos = True
    finally:
        conn.close()


def cargar_hechos() -> list[str]:
    """Retorna todos los hechos (sin filtro de similitud)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT hecho FROM hechos WHERE agente = %s ORDER BY timestamp ASC",
                (AGENTE,)
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def buscar_hechos_similares(query: str, top_k: int = TOP_K) -> list[str]:
    """Devuelve los hechos más relevantes para la query usando similitud vectorial."""
    embedding = get_embedding(query)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT hecho
                FROM hechos
                WHERE agente = %s AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (AGENTE, str(embedding), top_k)
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def _hay_hechos() -> bool:
    """Comprueba si existe algún hecho guardado. Cacheado en memoria durante la sesión."""
    global _cache_hay_hechos
    if _cache_hay_hechos is not None:
        return _cache_hay_hechos
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM hechos WHERE agente = %s LIMIT 1", (AGENTE,))
            _cache_hay_hechos = cur.fetchone() is not None
    finally:
        conn.close()
    return _cache_hay_hechos


def como_contexto(query: str = None) -> str:
    """Formatea hechos para inyectar al LLM.
    Si se pasa query, devuelve solo los más relevantes por similitud.
    Si no, devuelve todos."""
    if not _hay_hechos():
        return ""
    hechos = buscar_hechos_similares(query) if query else cargar_hechos()
    if not hechos:
        return ""
    lineas = "\n".join(f"- {h}" for h in hechos)
    return f"Hechos que recuerdo del usuario y el sistema:\n{lineas}"
