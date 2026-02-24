"""Memoria semántica — hechos clave del usuario y el sistema (persistencia JSON)."""

import json
import os
from datetime import datetime

_BASE = os.path.join(os.path.dirname(__file__), "..", "..")
SEMANTICA_FILE = os.path.abspath(os.path.join(_BASE, "memoria_semantica.json"))


def _cargar_raw() -> list:
    if not os.path.exists(SEMANTICA_FILE):
        return []
    with open(SEMANTICA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_raw(datos: list) -> None:
    with open(SEMANTICA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def guardar_hecho(hecho: str) -> None:
    datos = _cargar_raw()
    datos.append({"hecho": hecho, "timestamp": datetime.now().isoformat()})
    _guardar_raw(datos)


def cargar_hechos() -> list[str]:
    return [entry["hecho"] for entry in _cargar_raw()]


def como_contexto() -> str:
    hechos = cargar_hechos()
    if not hechos:
        return ""
    lineas = "\n".join(f"- {h}" for h in hechos)
    return f"Hechos que recuerdo del usuario y el sistema:\n{lineas}"
