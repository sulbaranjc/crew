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
    """Lista el contenido de un directorio. Usa rutas absolutas o ~ para el home."""
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
    """Busca archivos por nombre o patrón (ej: '*.py', 'config.json') en una ruta."""
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
    """Muestra información general del sistema: hostname, kernel, uptime."""
    hostname = _run(["hostname"])
    uname = _run(["uname", "-a"])
    uptime = _run(["uptime"])
    whoami = _run(["whoami"])
    return f"Usuario: {whoami}\nHostname: {hostname}\nUptime: {uptime}\nKernel: {uname}"


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
    return _run(["ps", "aux", "--sort=-%cpu"])


@tool
def info_red() -> str:
    """Muestra las interfaces de red y sus IPs."""
    return _run(["ip", "a"])


@tool
def paquetes_instalados(gestor: str = "dpkg") -> str:
    """Lista paquetes instalados. gestor puede ser 'dpkg', 'pip', 'pip3', 'snap', 'flatpak'."""
    cmds = {
        "dpkg":    ["dpkg", "-l"],
        "pip":     ["pip", "list"],
        "pip3":    ["pip3", "list"],
        "snap":    ["snap", "list"],
        "flatpak": ["flatpak", "list"],
    }
    cmd = cmds.get(gestor, cmds["dpkg"])
    out = _run(cmd)
    lineas = out.splitlines()[:80]
    return "\n".join(lineas)


@tool
def variables_entorno() -> str:
    """Muestra las variables de entorno del proceso actual."""
    return "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))


@tool
def ejecutar_comando_seguro(comando: str) -> str:
    """Ejecuta un comando de solo lectura del sistema. Solo se permiten comandos de inspección.
    Ejemplos válidos: 'ls /etc', 'cat /proc/cpuinfo', 'which python3', 'lscpu', 'lsblk'.
    NO se permite modificar, eliminar ni instalar nada."""
    PROHIBIDOS = ["rm", "mv", "cp", "chmod", "chown", "sudo", "su",
                  "dd", "mkfs", "fdisk", "apt", "pip install", "wget", "curl",
                  ">", ">>", "|", ";", "&", "kill", "pkill", "reboot", "shutdown"]
    for p in PROHIBIDOS:
        if p in comando:
            return f"[Bloqueado] El comando contiene '{p}' que no está permitido."
    partes = comando.split()
    return _run(partes, timeout=10)


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
    variables_entorno,
    ejecutar_comando_seguro,
]
