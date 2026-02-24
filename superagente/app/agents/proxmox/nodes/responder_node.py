import json
from langchain_core.messages import AIMessage, SystemMessage
from app.graph.state import SuperState
from app.llm.client import llm

SYSTEM_PROMPT = """Eres un asistente experto en infraestructura Proxmox VE.
Se te proporcionan datos crudos de la API de Proxmox. Tu tarea es resumirlos
en lenguaje natural, claro y conciso, destacando el estado general, nodos activos,
VMs/CTs corriendo, y cualquier problema detectado.
Si hay un error, explícalo de forma simple."""


def responder_node(state: SuperState) -> SuperState:
    tool_results = state.get("tool_results") or {}
    data_str = json.dumps(tool_results, ensure_ascii=False, indent=2)

    prompt_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
        SystemMessage(content=f"Datos de Proxmox:\n{data_str}"),
    ]
    resp = llm.invoke(prompt_messages)
    return {
        "messages": state["messages"] + [AIMessage(content=resp.content)],
        "agent": "proxmox",
        "tool_results": tool_results,
    }
