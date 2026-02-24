from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import json
import os


MODEL = "qwen2.5:7b-32k"
BASE_URL = "http://127.0.0.1:11434"
HISTORIAL_FILE = "historial_chat.json"


# ── Tools de sistema de archivos ─────────────────────────────────────────────

@tool
def crear_archivo(ruta: str, contenido: str) -> str:
    """Crea o sobreescribe un archivo en la ruta indicada con el contenido dado."""
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True) if os.path.dirname(ruta) else None
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"Archivo creado correctamente: {ruta}"
    except Exception as e:
        return f"Error al crear el archivo: {e}"


@tool
def leer_archivo(ruta: str) -> str:
    """Lee y devuelve el contenido de un archivo existente."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error al leer el archivo: {e}"


@tool
def listar_directorio(ruta: str) -> str:
    """Lista los archivos y carpetas dentro del directorio indicado."""
    try:
        entries = os.listdir(ruta)
        if not entries:
            return f"El directorio '{ruta}' está vacío."
        return "\n".join(sorted(entries))
    except Exception as e:
        return f"Error al listar el directorio: {e}"


@tool
def eliminar_archivo(ruta: str) -> str:
    """Elimina el archivo en la ruta indicada."""
    try:
        os.remove(ruta)
        return f"Archivo eliminado correctamente: {ruta}"
    except Exception as e:
        return f"Error al eliminar el archivo: {e}"


@tool
def cambiar_permisos(ruta: str, permisos: str) -> str:
    """Cambia los permisos de un archivo. Acepta notación octal como '755' o '644'."""
    try:
        os.chmod(ruta, int(permisos, 8))
        return f"Permisos de '{ruta}' cambiados a {permisos}"
    except Exception as e:
        return f"Error al cambiar permisos: {e}"


# ── LLM + tools ──────────────────────────────────────────────────────────────

tools = [crear_archivo, leer_archivo, listar_directorio, eliminar_archivo, cambiar_permisos]
llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0.2)
llm_with_tools = llm.bind_tools(tools)


# ── Grafo ─────────────────────────────────────────────────────────────────────

class State(TypedDict):
    messages: List[BaseMessage]


def chat_node(state: State) -> State:
    resp = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [resp]}


graph = StateGraph(State)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")

app = graph.compile()


# ── Historial ─────────────────────────────────────────────────────────────────

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
        elif isinstance(m, AIMessage) and isinstance(m.content, str):
            datos.append({"type": "ai", "content": m.content})
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    state: State = {"messages": cargar_historial()}
    print("Chatty (LangGraph + Ollama + tools). Escribe 'salir' para terminar.\n")
    if state["messages"]:
        print("Historial cargado:")
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                print("Tú:", m.content)
            elif isinstance(m, AIMessage) and isinstance(m.content, str):
                print("Chatty:", m.content)
        print()
    while True:
        user = input("Tú: ").strip()
        if user.lower() in {"salir", "exit", "quit"}:
            break
        state["messages"].append(HumanMessage(content=user))
        state = app.invoke(state)
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and isinstance(last.content, str):
            print("Chatty:", last.content, "\n")
        guardar_historial(state["messages"])
