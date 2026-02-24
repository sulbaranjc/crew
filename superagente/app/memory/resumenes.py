"""Memoria de resúmenes — resúmenes de sesiones anteriores (persistencia JSON)."""

import json
import os
from datetime import datetime

_BASE = os.path.join(os.path.dirname(__file__), "..", "..")
RESUMENES_FILE = os.path.abspath(os.path.join(_BASE, "memoria_resumenes.json"))


def _cargar_raw() -> list:
    if not os.path.exists(RESUMENES_FILE):
        return []
    with open(RESUMENES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_raw(datos: list) -> None:
    with open(RESUMENES_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def guardar_resumen(resumen: str) -> None:
    datos = _cargar_raw()
    datos.append({"resumen": resumen, "timestamp": datetime.now().isoformat()})
    _guardar_raw(datos)


def cargar_resumenes() -> list[str]:
    return [entry["resumen"] for entry in _cargar_raw()]


def como_contexto() -> str:
    resumenes = cargar_resumenes()
    if not resumenes:
        return ""
    lineas = "\n".join(f"- {r}" for r in resumenes)
    return f"Resúmenes de conversaciones anteriores:\n{lineas}"
