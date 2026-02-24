from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, AIMessage
from app.llm.client import llm
from app.graph.state import SuperState
from app.tools.sistema import SISTEMA_TOOLS

SYSTEM_PROMPT = """Eres un asistente personal experto en Linux con acceso completo al sistema del usuario.
Tienes herramientas para explorar archivos, procesos, disco, red, paquetes y más.

Cuando el usuario te pida algo:
1. Usa las herramientas necesarias para obtener la información real del sistema.
2. Puedes encadenar varias herramientas si necesitas más contexto.
3. Responde de forma clara y organizada en español.
4. Si encuentras algo relevante que el usuario no pidió explícitamente pero es importante, menciónalo.

REGLAS:
- Solo lectura. No modifiques, elimines ni instales nada.
- Si el usuario pide algo destructivo, explica que solo tienes permisos de lectura.
- Si no encuentras algo, dilo claramente y sugiere dónde más buscar."""

_react_agent = create_react_agent(llm, SISTEMA_TOOLS)


def sistema_agent_node(state: SuperState) -> SuperState:
    mensajes_con_sistema = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    resultado = _react_agent.invoke({"messages": mensajes_con_sistema})
    respuesta_final = resultado["messages"][-1]
    return {
        "messages": state["messages"] + [AIMessage(content=respuesta_final.content)],
        "agent": "sistema",
        "tool_results": None,
    }
