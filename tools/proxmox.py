"""Tools de Proxmox VE — consultas de solo lectura via API."""

import json
import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_PVE_URL           = os.environ.get("PVE_URL", "").rstrip("/")
_PVE_TOKEN_ID      = os.environ.get("PVE_TOKEN_ID", "")
_PVE_TOKEN_SECRET  = os.environ.get("PVE_TOKEN_SECRET", "")
_PVE_VERIFY_SSL    = os.environ.get("PVE_VERIFY_SSL", "false").lower() == "true"

PROXMOX_ENABLED = bool(_PVE_URL and _PVE_TOKEN_ID and _PVE_TOKEN_SECRET)


def _get(path: str) -> dict | list:
    if not PROXMOX_ENABLED:
        return {"error": "Proxmox no configurado. Añade PVE_URL, PVE_TOKEN_ID y PVE_TOKEN_SECRET al .env"}
    s = requests.Session()
    s.verify = _PVE_VERIFY_SSL
    s.headers["Authorization"] = f"PVEAPIToken={_PVE_TOKEN_ID}={_PVE_TOKEN_SECRET}"
    r = s.get(f"{_PVE_URL}/api2/json{path}", timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})


@tool
def proxmox_nodos() -> str:
    """Lista los nodos del cluster Proxmox con su estado, CPU y memoria."""
    data = _get("/nodes")
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    lineas = []
    for n in data:
        estado = n.get("status", "?")
        cpu = f"{n.get('cpu', 0)*100:.1f}%"
        mem_used = n.get("mem", 0) / 1024**3
        mem_total = n.get("maxmem", 0) / 1024**3
        lineas.append(f"- {n['node']}: {estado} | CPU {cpu} | RAM {mem_used:.1f}/{mem_total:.1f} GB")
    return "\n".join(lineas) if lineas else "Sin nodos."


@tool
def proxmox_vms() -> str:
    """Lista todas las VMs y contenedores LXC del cluster con estado y recursos."""
    data = _get("/cluster/resources")
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    recursos = [r for r in data if r.get("type") in ("qemu", "lxc")]
    if not recursos:
        return "Sin VMs ni contenedores."
    lineas = []
    for r in sorted(recursos, key=lambda x: (x.get("node", ""), x.get("vmid", 0))):
        tipo = "VM " if r["type"] == "qemu" else "LXC"
        estado = r.get("status", "?")
        cpu = f"{r.get('cpu', 0)*100:.1f}%"
        mem = r.get("mem", 0) / 1024**2
        lineas.append(f"- [{tipo}] {r.get('name','?')} (ID:{r.get('vmid','?')}) nodo:{r.get('node','?')} | {estado} | CPU {cpu} | RAM {mem:.0f} MB")
    return "\n".join(lineas)


@tool
def proxmox_cluster() -> str:
    """Muestra el estado general del cluster Proxmox (quorum, nodos, etc.)."""
    data = _get("/cluster/status")
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    return json.dumps(data, indent=2, ensure_ascii=False)


@tool
def proxmox_version() -> str:
    """Muestra la versión de Proxmox VE instalada."""
    data = _get("/version")
    if isinstance(data, dict) and "error" in data:
        return data["error"]
    return f"Proxmox VE {data.get('version', '?')} (release {data.get('release', '?')})"


PROXMOX_TOOLS = [proxmox_nodos, proxmox_vms, proxmox_cluster, proxmox_version]
