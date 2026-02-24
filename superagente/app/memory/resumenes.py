"""Memoria de resúmenes — resúmenes de sesiones anteriores (PostgreSQL)."""

from datetime import datetime
from .db import get_conn

AGENTE = "superagente"


def guardar_resumen(resumen: str) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO resumenes (agente, resumen, timestamp) VALUES (%s, %s, %s)",
                (AGENTE, resumen, datetime.now())
            )
        conn.commit()
    finally:
        conn.close()


def cargar_resumenes() -> list[str]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT resumen FROM resumenes WHERE agente = %s ORDER BY timestamp ASC",
                (AGENTE,)
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def como_contexto() -> str:
    resumenes = cargar_resumenes()
    if not resumenes:
        return ""
    lineas = "\n".join(f"- {r}" for r in resumenes)
    return f"Resumenes de conversaciones anteriores:\n{lineas}"
