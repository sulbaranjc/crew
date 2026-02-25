"""Tools de sistema: archivos, procesos, red y monitoreo."""

import os
import subprocess
from langchain_core.tools import tool

MAX_FILE_CHARS = 8000
MAX_RESULTS = 60


def _run(cmd: list, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip() or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "[Error] Comando tardó demasiado."
    except Exception as e:
        return f"[Error] {e}"


@tool
def listar_directorio(ruta: str) -> str:
    """Lista el contenido de un directorio con tipo y tamaño. Usa rutas absolutas o ~ para el home."""
    try:
        ruta = os.path.expanduser(ruta)
        entradas = sorted(os.scandir(ruta), key=lambda e: (not e.is_dir(), e.name))
        lineas = []
        for e in entradas[:MAX_RESULTS]:
            tipo = "DIR " if e.is_dir() else "FILE"
            try:
                size = e.stat().st_size
            except Exception:
                size = 0
            lineas.append(f"{tipo}  {size:>10}  {e.name}")
        if not lineas:
            return "(directorio vacío)"
        return "\n".join(lineas)
    except Exception as ex:
        return f"[Error] {ex}"


@tool
def leer_archivo(ruta: str) -> str:
    """Lee el contenido de un archivo de texto. Máximo 8000 caracteres."""
    try:
        ruta = os.path.expanduser(ruta)
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read(MAX_FILE_CHARS)
        if len(contenido) == MAX_FILE_CHARS:
            contenido += "\n...[truncado — archivo muy largo]"
        return contenido
    except Exception as ex:
        return f"[Error] {ex}"


@tool
def buscar_archivos(patron: str, ruta_base: str = "~") -> str:
    """Busca archivos por nombre o patrón glob (ej: '*.py', 'config.json') en una ruta."""
    ruta_base = os.path.expanduser(ruta_base)
    out = _run(["find", ruta_base, "-name", patron, "-maxdepth", "10",
                "-not", "-path", "*/.*"])
    lineas = [l for l in out.splitlines() if l][:MAX_RESULTS]
    return "\n".join(lineas) if lineas else "Sin resultados."


@tool
def buscar_contenido(texto: str, ruta_base: str = "~", extension: str = "*") -> str:
    """Busca un texto dentro de archivos. Devuelve los archivos que lo contienen."""
    ruta_base = os.path.expanduser(ruta_base)
    out = _run(["grep", "-r", "--include", f"*.{extension}", "-l", texto, ruta_base])
    lineas = [l for l in out.splitlines() if l][:MAX_RESULTS]
    return "\n".join(lineas) if lineas else "Sin resultados."


@tool
def info_sistema() -> str:
    """Muestra información general del sistema: hostname, kernel, uptime, usuario."""
    return "\n".join([
        f"Usuario: {_run(['whoami'])}",
        f"Hostname: {_run(['hostname'])}",
        f"Uptime: {_run(['uptime'])}",
        f"Kernel: {_run(['uname', '-a'])}",
    ])


@tool
def uso_disco() -> str:
    """Muestra el uso de disco de todas las particiones montadas."""
    return _run(["df", "-h"])


@tool
def uso_memoria() -> str:
    """Muestra el uso de memoria RAM y swap."""
    return _run(["free", "-h"])


@tool
def procesos_activos() -> str:
    """Lista los procesos en ejecución ordenados por uso de CPU."""
    out = _run(["ps", "aux", "--sort=-%cpu"])
    return "\n".join(out.splitlines()[:30])


@tool
def info_red() -> str:
    """Muestra las interfaces de red y sus IPs."""
    return _run(["ip", "a"])


@tool
def paquetes_instalados(gestor: str = "dpkg") -> str:
    """Lista paquetes instalados. gestor puede ser 'dpkg', 'pip3', 'snap', 'flatpak'."""
    cmds = {
        "dpkg":    ["dpkg", "-l"],
        "pip3":    ["pip3", "list"],
        "snap":    ["snap", "list"],
        "flatpak": ["flatpak", "list"],
    }
    out = _run(cmds.get(gestor, cmds["dpkg"]))
    return "\n".join(out.splitlines()[:80])


@tool
def ejecutar_comando_seguro(comando: str) -> str:
    """Ejecuta un comando de solo lectura del sistema (inspección). Ejemplos: 'lscpu', 'lsblk',
    'cat /proc/cpuinfo', 'which python3'. NO se permite modificar, eliminar ni instalar nada."""
    PROHIBIDOS = ["rm", "mv", "cp", "chmod", "chown", "sudo", "su", "dd", "mkfs",
                  "fdisk", "apt", "pip install", "wget", "curl", ">", ">>",
                  "kill", "pkill", "reboot", "shutdown"]
    for p in PROHIBIDOS:
        if p in comando:
            return f"[Bloqueado] El comando contiene '{p}' que no está permitido."
    return _run(comando.split(), timeout=10)


SISTEMA_TOOLS = [
    listar_directorio,
    leer_archivo,
    buscar_archivos,
    buscar_contenido,
    info_sistema,
    uso_disco,
    uso_memoria,
    procesos_activos,
    info_red,
    paquetes_instalados,
    ejecutar_comando_seguro,
]
