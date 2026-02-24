from langgraph.graph import StateGraph, END
from app.graph.state import SuperState
from app.graph.nodes.router_node import router_node
from app.agents.chat.graph import chat_graph
from app.agents.proxmox.graph import proxmox_graph
from app.agents.sistema.graph import sistema_agent_node


def route_to_agent(state: SuperState) -> str:
    return state.get("agent", "chat")


def chat_agent_node(state: SuperState) -> SuperState:
    return chat_graph.invoke(state)


def proxmox_agent_node(state: SuperState) -> SuperState:
    return proxmox_graph.invoke(state)


def build_orchestrator():
    g = StateGraph(SuperState)

    g.add_node("router", router_node)
    g.add_node("chat_agent", chat_agent_node)
    g.add_node("proxmox_agent", proxmox_agent_node)
    g.add_node("sistema_agent", sistema_agent_node)

    g.set_entry_point("router")

    g.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "chat":    "chat_agent",
            "proxmox": "proxmox_agent",
            "sistema": "sistema_agent",
        },
    )

    g.add_edge("chat_agent", END)
    g.add_edge("proxmox_agent", END)
    g.add_edge("sistema_agent", END)

    return g.compile()


orchestrator = build_orchestrator()
