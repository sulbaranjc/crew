"""Memoria episódica — historial de conversación (persistencia JSON)."""

import json
import os
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODICA_FILE = os.path.join(_BASE, "memoria_episodica.json")

# Migración automática desde archivo legacy
_LEGACY_FILE = os.path.join(_BASE, "historial_chat.json")


def cargar() -> List[BaseMessage]:
    archivo = EPISODICA_FILE if os.path.exists(EPISODICA_FILE) else _LEGACY_FILE
    if not os.path.exists(archivo):
        return []
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)
    mensajes = []
    for m in datos:
        if m["type"] == "human":
            mensajes.append(HumanMessage(content=m["content"]))
        elif m["type"] == "ai":
            mensajes.append(AIMessage(content=m["content"]))
    return mensajes


def guardar(mensajes: List[BaseMessage]) -> None:
    datos = []
    for m in mensajes:
        if isinstance(m, HumanMessage):
            datos.append({"type": "human", "content": m.content})
        elif isinstance(m, AIMessage) and isinstance(m.content, str):
            datos.append({"type": "ai", "content": m.content})
    with open(EPISODICA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
