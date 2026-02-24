"""Memoria episódica — historial de conversación (PostgreSQL)."""

from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from .db import get_conn

AGENTE = "superagente"


def cargar() -> List[BaseMessage]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM conversaciones "
                "WHERE agente = %s ORDER BY timestamp ASC",
                (AGENTE,)
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    mensajes = []
    for role, content in rows:
        if role == "human":
            mensajes.append(HumanMessage(content=content))
        elif role == "ai":
            mensajes.append(AIMessage(content=content))
    return mensajes


def guardar(mensajes: List[BaseMessage]) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversaciones WHERE agente = %s", (AGENTE,))
            for m in mensajes:
                if isinstance(m, HumanMessage):
                    cur.execute(
                        "INSERT INTO conversaciones (agente, role, content) VALUES (%s, %s, %s)",
                        (AGENTE, "human", m.content)
                    )
                elif isinstance(m, AIMessage) and isinstance(m.content, str):
                    cur.execute(
                        "INSERT INTO conversaciones (agente, role, content) VALUES (%s, %s, %s)",
                        (AGENTE, "ai", m.content)
                    )
        conn.commit()
    finally:
        conn.close()
