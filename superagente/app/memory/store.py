"""Interfaz unificada de memoria — re-exporta los 3 módulos."""

from .episodica import cargar, guardar
from .semantica import guardar_hecho, cargar_hechos, como_contexto as contexto_semantico
from .resumenes import guardar_resumen, cargar_resumenes, como_contexto as contexto_resumenes


# Aliases de compatibilidad para no romper imports existentes
def cargar_historial():
    return cargar()


def guardar_historial(mensajes):
    guardar(mensajes)


__all__ = [
    "cargar", "guardar",
    "cargar_historial", "guardar_historial",
    "guardar_hecho", "cargar_hechos", "contexto_semantico",
    "guardar_resumen", "cargar_resumenes", "contexto_resumenes",
]
