"""Tool SSH para Proxmox VE — usa el alias 'ssh pve' del sistema (sin credenciales en .env)."""

import subprocess
from langchain_core.tools import tool
from memory.semantica import guardar_hecho

SSH_ALIAS = "pve"
SSH_ENABLED = True  # Siempre activo — depende de que 'ssh pve' esté configurado en ~/.ssh/config

_PROHIBIDOS = ["rm", "mv", "cp", "chmod", "chown", "dd", "mkfs", "fdisk",
               "apt", "dpkg -i", "reboot", "shutdown", "kill", "pkill",
               "passwd", "userdel", ">", ">>", "curl -o", "wget -O"]


def _ssh(comando: str, timeout: int = 30) -> str:
    for p in _PROHIBIDOS:
        if p in comando:
            return f"[Bloqueado] Comando no permitido: '{p}'"
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", SSH_ALIAS, comando],
            capture_output=True, text=True, timeout=timeout
        )
        salida = r.stdout.strip() or r.stderr.strip() or "(sin salida)"
        return salida
    except subprocess.TimeoutExpired:
        return "[Error] El comando tardó demasiado."
    except Exception as e:
        return f"[Error SSH] {e}"


@tool
def pve_ejecutar(comando: str) -> str:
    """Ejecuta un comando de solo lectura en el servidor Proxmox VE via SSH.
    Ejemplos: 'qm list', 'pct list', 'pvesh get /nodes', 'df -h', 'cat /etc/pve-release',
    'systemctl status pve-cluster', 'pvesm status'."""
    return _ssh(comando)


@tool
def pve_vms() -> str:
    """Lista todas las VMs (QEMU/KVM) del servidor Proxmox con su estado y recursos."""
    return _ssh("qm list")


@tool
def pve_contenedores() -> str:
    """Lista todos los contenedores LXC del servidor Proxmox con su estado."""
    return _ssh("pct list")


@tool
def pve_almacenamiento() -> str:
    """Muestra el uso de almacenamiento en el servidor Proxmox."""
    return _ssh("pvesm status")


@tool
def pve_version() -> str:
    """Muestra la versión de Proxmox VE instalada."""
    return _ssh("pveversion")


@tool
def pve_logs(servicio: str = "pve-cluster") -> str:
    """Muestra los últimos 30 logs de un servicio Proxmox.
    Servicios: pvedaemon, pvestatd, corosync, pve-firewall, pve-cluster."""
    return _ssh(f"journalctl -u {servicio} -n 30 --no-pager")


@tool
def pve_ups() -> str:
    """Muestra el estado actual del UPS (SAI) conectado al servidor Proxmox:
    carga de batería, voltaje, carga conectada y tiempo restante."""
    return _ssh("~/scripts/estado_ups.sh")


@tool
def pve_explorar() -> str:
    """Explora el servidor Proxmox de forma completa: versión, nodos, VMs, contenedores,
    almacenamiento y recursos. Guarda automáticamente los hallazgos en la memoria semántica."""
    hallazgos = {}

    hallazgos["version"]        = _ssh("pveversion")
    hallazgos["vms"]            = _ssh("qm list")
    hallazgos["contenedores"]   = _ssh("pct list")
    hallazgos["almacenamiento"] = _ssh("pvesm status")
    hallazgos["disco"]          = _ssh("df -h")
    hallazgos["memoria"]        = _ssh("free -h")
    hallazgos["nodos"]          = _ssh("pvesh get /nodes --output-format=json-pretty 2>/dev/null | head -50")

    # Guardar hallazgos relevantes en memoria semántica
    if not hallazgos["version"].startswith("[Error"):
        guardar_hecho(f"Proxmox versión: {hallazgos['version']}")
    if not hallazgos["vms"].startswith("[Error") and hallazgos["vms"] != "(sin salida)":
        guardar_hecho(f"VMs en Proxmox:\n{hallazgos['vms']}")
    if not hallazgos["contenedores"].startswith("[Error") and hallazgos["contenedores"] != "(sin salida)":
        guardar_hecho(f"Contenedores LXC en Proxmox:\n{hallazgos['contenedores']}")
    if not hallazgos["almacenamiento"].startswith("[Error"):
        guardar_hecho(f"Almacenamiento Proxmox:\n{hallazgos['almacenamiento']}")

    # Construir resumen legible
    lineas = ["=== Exploración Proxmox ==="]
    for clave, valor in hallazgos.items():
        lineas.append(f"\n--- {clave.upper()} ---\n{valor}")
    lineas.append("\n✓ Hallazgos guardados en memoria.")
    return "\n".join(lineas)


SSH_PVE_TOOLS = [
    pve_ejecutar,
    pve_ups,
    pve_explorar,
]
