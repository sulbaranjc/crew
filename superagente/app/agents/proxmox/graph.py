from langgraph.graph import StateGraph, END
from app.graph.state import SuperState
from app.agents.proxmox.nodes.executor_node import executor_node
from app.agents.proxmox.nodes.responder_node import responder_node


def build_proxmox_graph():
    g = StateGraph(SuperState)
    g.add_node("executor", executor_node)
    g.add_node("responder", responder_node)
    g.set_entry_point("executor")
    g.add_edge("executor", "responder")
    g.add_edge("responder", END)
    return g.compile()


proxmox_graph = build_proxmox_graph()
