import json
import os
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

HISTORIAL_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "historial.json")
HISTORIAL_FILE = os.path.abspath(HISTORIAL_FILE)


def cargar_historial() -> List[BaseMessage]:
    if not os.path.exists(HISTORIAL_FILE):
        return []
    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        datos = json.load(f)
    mensajes = []
    for m in datos:
        if m["type"] == "human":
            mensajes.append(HumanMessage(content=m["content"]))
        elif m["type"] == "ai":
            mensajes.append(AIMessage(content=m["content"]))
    return mensajes


def guardar_historial(mensajes: List[BaseMessage]) -> None:
    datos = []
    for m in mensajes:
        if isinstance(m, HumanMessage):
            datos.append({"type": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            datos.append({"type": "ai", "content": m.content})
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
