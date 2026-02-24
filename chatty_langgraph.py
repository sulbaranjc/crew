from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import json
import os


MODEL = "qwen2.5:7b-32k"
BASE_URL = "http://127.0.0.1:11434"
HISTORIAL_FILE = "historial_chat.json"

llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0.2)

class State(TypedDict):
    messages: List[BaseMessage]

def chat_node(state: State) -> State:
    resp = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [AIMessage(content=resp.content)]}

graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.set_entry_point("chat")
graph.add_edge("chat", END)

app = graph.compile()

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            mensajes = []
            for m in datos:
                if m["type"] == "human":
                    mensajes.append(HumanMessage(content=m["content"]))
                elif m["type"] == "ai":
                    mensajes.append(AIMessage(content=m["content"]))
            return mensajes
    return []

def guardar_historial(mensajes):
    datos = []
    for m in mensajes:
        if isinstance(m, HumanMessage):
            datos.append({"type": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            datos.append({"type": "ai", "content": m.content})
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    state: State = {"messages": cargar_historial()}
    print("Chatty (LangGraph + Ollama). Escribe 'salir' para terminar.\n")
    if state["messages"]:
        print("Historial cargado:")
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                print("Tú:", m.content)
            elif isinstance(m, AIMessage):
                print("Chatty:", m.content)
        print()
    while True:
        user = input("Tú: ").strip()
        if user.lower() in {"salir", "exit", "quit"}:
            break
        state["messages"].append(HumanMessage(content=user))
        state = app.invoke(state)
        print("Chatty:", state["messages"][-1].content, "\n")
        guardar_historial(state["messages"])