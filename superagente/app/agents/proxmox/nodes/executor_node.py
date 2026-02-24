from app.graph.state import SuperState
from app.config.settings import PROXMOX_ENABLED
from app.tools.proxmox_api import ProxmoxAPI


def executor_node(state: SuperState) -> SuperState:
    if not PROXMOX_ENABLED:
        return {
            **state,
            "tool_results": {"error": "Proxmox no configurado. Revisa el archivo .env."},
        }
    try:
        api = ProxmoxAPI()
        results = {
            "nodes": api.nodes().get("data", []),
            "cluster_status": api.cluster_status().get("data", []),
            "cluster_resources": api.cluster_resources().get("data", []),
        }
    except Exception as e:
        results = {"error": str(e)}

    return {**state, "tool_results": results}
