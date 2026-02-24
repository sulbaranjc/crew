"""Memoria semántica — hechos clave del usuario (PostgreSQL)."""

from datetime import datetime
from .db import get_conn

AGENTE = "superagente"


def guardar_hecho(hecho: str) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hechos (agente, hecho, timestamp) VALUES (%s, %s, %s)",
                (AGENTE, hecho, datetime.now())
            )
        conn.commit()
    finally:
        conn.close()


def cargar_hechos() -> list[str]:
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


def como_contexto() -> str:
    hechos = cargar_hechos()
    if not hechos:
        return ""
    lineas = "\n".join(f"- {h}" for h in hechos)
    return f"Hechos que recuerdo del usuario y el sistema:\n{lineas}"
