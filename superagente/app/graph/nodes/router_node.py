from langchain_core.messages import SystemMessage
from app.graph.state import SuperState
from app.llm.client import llm

ROUTER_PROMPT = """Eres un clasificador de intenciones. Analiza el último mensaje del usuario
y responde ÚNICAMENTE con una de estas palabras (sin explicación adicional):

- proxmox  → si el usuario pregunta sobre infraestructura, VMs, nodos, cluster, Proxmox, servidores remotos, recursos del hypervisor
- sistema  → si el usuario pregunta sobre SU laptop/computadora local: archivos, carpetas, procesos, disco, RAM, red local, paquetes instalados, buscar algo en el sistema, ver logs locales, info del sistema operativo
- chat     → cualquier otra cosa (saludos, preguntas generales, dudas, conversación)

Solo responde con una palabra: proxmox, sistema o chat."""


def router_node(state: SuperState) -> SuperState:
    classification_messages = [
        SystemMessage(content=ROUTER_PROMPT),
        state["messages"][-1],  # solo el último mensaje del usuario
    ]
    resp = llm.invoke(classification_messages)
    intent = resp.content.strip().lower()

    if "proxmox" in intent:
        agent = "proxmox"
    elif "sistema" in intent:
        agent = "sistema"
    else:
        agent = "chat"

    return {**state, "agent": agent}
