from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
import os

from memory.episodica import cargar, guardar
from memory.semantica import guardar_hecho, cargar_hechos, como_contexto as contexto_semantico
from memory.resumenes import como_contexto as contexto_resumenes

MODEL = "qwen2.5:latest"
BASE_URL = "http://127.0.0.1:11434"


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


@tool
def dia_de_la_semana(fecha: str) -> str:
    """Calcula el día de la semana de una fecha. Formato: DD/MM/YYYY o YYYY-MM-DD."""
    from datetime import date as _date
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    try:
        if "/" in fecha:
            partes = fecha.strip().split("/")
            if len(partes[2]) == 4:
                d = _date(int(partes[2]), int(partes[1]), int(partes[0]))
            else:
                d = _date(int(partes[0]), int(partes[1]), int(partes[2]))
        else:
            partes = fecha.strip().split("-")
            d = _date(int(partes[0]), int(partes[1]), int(partes[2]))
        return f"{fecha} fue un {dias[d.weekday()]}"
    except Exception as e:
        return f"Error al calcular la fecha: {e}"


# ── Memoria semántica ─────────────────────────────────────────────────────────

@tool
def recordar_hecho(hecho: str) -> str:
    """Guarda un hecho importante sobre el usuario en la memoria semántica persistente.
    Úsala siempre que el usuario comparta datos personales: nombre, trabajo, ciudad,
    preferencias, habilidades o cualquier información relevante sobre él."""
    guardar_hecho(hecho)
    return f"Recordado: {hecho}"


@tool
def ver_lo_que_recuerdo() -> str:
    """Muestra todos los hechos que recuerdas sobre el usuario."""
    hechos = cargar_hechos()
    if not hechos:
        return "No tengo ningún dato guardado sobre ti todavía."
    return "Lo que recuerdo de ti:\n" + "\n".join(f"- {h}" for h in hechos)


# ── LLM + tools ──────────────────────────────────────────────────────────────

tools = [crear_archivo, leer_archivo, listar_directorio, eliminar_archivo,
         cambiar_permisos, recordar_hecho, ver_lo_que_recuerdo, dia_de_la_semana]
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


# ── CLI ───────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres Chatty, un asistente personal. Sigue estas reglas sin excepción:
1. Tu nombre es CHATTY. Nunca digas que te llamas Qwen, Woen ni ningún otro nombre.
2. Responde ÚNICAMENTE en español. PROHIBIDO usar caracteres chinos (汉字), japoneses (ひらがな) ni coreanos (한글).
3. Si detectas que ibas a escribir un carácter asiático, sustitúyelo por la palabra en español.
4. Sé directo y conciso.
5. MEMORIA: Cuando el usuario comparta datos personales (nombre, trabajo, ciudad, estudios,
   preferencias, etc.), llama INMEDIATAMENTE a la tool `recordar_hecho` para guardarlos.
   No esperes a que te lo pidan — hazlo de forma proactiva y silenciosa.
6. FECHAS: Para calcular el día de la semana de cualquier fecha, SIEMPRE usa la tool
   `dia_de_la_semana`. NUNCA calcules fechas de memoria — siempre puedes equivocarte."""

if __name__ == "__main__":
    mensajes_iniciales = cargar()

    # System prompt base (siempre primero)
    sistema = SYSTEM_PROMPT

    # Añadir contexto de memoria semántica y resúmenes si existen
    contexto = "\n\n".join(filter(None, [contexto_resumenes(), contexto_semantico()]))
    if contexto:
        sistema += "\n\n" + contexto

    mensajes_iniciales = [SystemMessage(content=sistema)] + mensajes_iniciales
    state: State = {"messages": mensajes_iniciales}
    print("Chatty (LangGraph + Ollama + tools). Escribe 'salir' para terminar.\n")

    for m in mensajes_iniciales:
        if isinstance(m, HumanMessage):
            print("👨 Tú:", m.content)
        elif isinstance(m, AIMessage) and isinstance(m.content, str):
            print("🦂 Chatty:", m.content)
    if mensajes_iniciales:
        print()

    while True:
        user = input("👨 Tú: ").strip()
        if user.lower() in {"salir", "exit", "quit"}:
            break
        # Actualizar contexto semántico relevante para este mensaje
        ctx_sem = contexto_semantico(user)
        if ctx_sem:
            state["messages"] = [
                m for m in state["messages"] if not isinstance(m, SystemMessage)
            ]
            state["messages"] = [SystemMessage(content=SYSTEM_PROMPT + "\n\n" + ctx_sem + "\n\n" + contexto_resumenes())] + state["messages"]

        state["messages"].append(HumanMessage(content=user))
        state = app.invoke(state)
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and isinstance(last.content, str):
            print("🦂 Chatty:", last.content, "\n")
        guardar(state["messages"])
