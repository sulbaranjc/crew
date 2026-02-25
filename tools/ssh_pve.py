"""Tool SSH de solo lectura para ejecutar comandos en el servidor Proxmox VE."""

import os
import paramiko
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_SSH_HOST     = os.environ.get("PVE_SSH_HOST", "")
_SSH_PORT     = int(os.environ.get("PVE_SSH_PORT", "22"))
_SSH_USER     = os.environ.get("PVE_SSH_USER", "root")
_SSH_PASSWORD = os.environ.get("PVE_SSH_PASSWORD", "")
_SSH_KEY_PATH = os.environ.get("PVE_SSH_KEY", "")

SSH_ENABLED = bool(_SSH_HOST and (_SSH_PASSWORD or _SSH_KEY_PATH))

# Comandos permitidos (solo lectura / inspección)
_PERMITIDOS = [
    "cat", "ls", "df", "free", "uname", "hostname", "uptime", "whoami",
    "pvesh", "pvesm", "qm", "pct", "pveum", "pveversion", "pveceph",
    "systemctl status", "journalctl", "ip", "ss", "netstat", "ps",
    "top -bn1", "lscpu", "lsblk", "lspci", "dmidecode",
]
_PROHIBIDOS = ["rm", "mv", "cp", "chmod", "chown", "dd", "mkfs", "fdisk",
               "apt", "dpkg -i", "wget", "curl -o", "reboot", "shutdown",
               "kill", "pkill", ">", ">>", "passwd", "userdel"]


def _es_seguro(comando: str) -> bool:
    for p in _PROHIBIDOS:
        if p in comando:
            return False
    return True


def _ejecutar_ssh(comando: str) -> str:
    if not SSH_ENABLED:
        return "SSH a Proxmox no configurado. Añade PVE_SSH_HOST y PVE_SSH_PASSWORD (o PVE_SSH_KEY) al .env"
    if not _es_seguro(comando):
        return f"[Bloqueado] Comando no permitido por seguridad."
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if _SSH_KEY_PATH:
            client.connect(_SSH_HOST, port=_SSH_PORT, username=_SSH_USER,
                           key_filename=_SSH_KEY_PATH, timeout=15)
        else:
            client.connect(_SSH_HOST, port=_SSH_PORT, username=_SSH_USER,
                           password=_SSH_PASSWORD, timeout=15)
        _, stdout, stderr = client.exec_command(comando, timeout=30)
        salida = stdout.read().decode("utf-8", errors="replace").strip()
        error  = stderr.read().decode("utf-8", errors="replace").strip()
        client.close()
        return salida or error or "(sin salida)"
    except Exception as e:
        return f"[Error SSH] {e}"


@tool
def pve_ejecutar(comando: str) -> str:
    """Ejecuta un comando de solo lectura en el servidor Proxmox VE via SSH.
    Útil para inspeccionar VMs, contenedores, almacenamiento, logs y estado del sistema.
    Ejemplos: 'qm list', 'pct list', 'pvesh get /nodes', 'df -h', 'systemctl status pve-cluster'."""
    return _ejecutar_ssh(comando)


@tool
def pve_version() -> str:
    """Muestra la versión de Proxmox VE instalada en el servidor."""
    return _ejecutar_ssh("pveversion")


@tool
def pve_vms() -> str:
    """Lista todas las VMs (QEMU) del servidor Proxmox con su estado."""
    return _ejecutar_ssh("qm list")


@tool
def pve_contenedores() -> str:
    """Lista todos los contenedores LXC del servidor Proxmox con su estado."""
    return _ejecutar_ssh("pct list")


@tool
def pve_almacenamiento() -> str:
    """Muestra el uso de almacenamiento en el servidor Proxmox."""
    return _ejecutar_ssh("pvesm status")


@tool
def pve_logs(servicio: str = "pve-cluster") -> str:
    """Muestra los últimos logs de un servicio de Proxmox. Por defecto: pve-cluster.
    Otros servicios: pvedaemon, pvestatd, corosync, pve-firewall."""
    return _ejecutar_ssh(f"journalctl -u {servicio} -n 30 --no-pager")


SSH_PVE_TOOLS = [
    pve_ejecutar,
    pve_version,
    pve_vms,
    pve_contenedores,
    pve_almacenamiento,
    pve_logs,
]
