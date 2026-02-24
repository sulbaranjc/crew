from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from app.graph.state import SuperState
from app.llm.client import llm


def chat_node(state: SuperState) -> SuperState:
    resp = llm.invoke(state["messages"])
    return {
        "messages": state["messages"] + [AIMessage(content=resp.content)],
        "agent": "chat",
        "tool_results": None,
    }


def build_chat_graph():
    g = StateGraph(SuperState)
    g.add_node("chat", chat_node)
    g.set_entry_point("chat")
    g.add_edge("chat", END)
    return g.compile()


chat_graph = build_chat_graph()
