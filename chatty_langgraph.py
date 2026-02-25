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
from tools.sistema import SISTEMA_TOOLS
from tools.proxmox import PROXMOX_TOOLS, PROXMOX_ENABLED

MODEL = "qwen2.5:latest"
BASE_URL = "http://127.0.0.1:11434"


# ── Tools exclusivas de Chatty ────────────────────────────────────────────────

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


# ── Registro de tools ─────────────────────────────────────────────────────────

CHATTY_TOOLS = [
    crear_archivo, eliminar_archivo, cambiar_permisos,
    recordar_hecho, ver_lo_que_recuerdo, dia_de_la_semana,
]

tools = CHATTY_TOOLS + SISTEMA_TOOLS + PROXMOX_TOOLS


# ── LLM + grafo ───────────────────────────────────────────────────────────────

llm = ChatOllama(model=MODEL, base_url=BASE_URL, temperature=0.2)
llm_with_tools = llm.bind_tools(tools)


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

def _describir_tools() -> str:
    grupos = {
        "Archivos y sistema": ["crear_archivo", "eliminar_archivo", "cambiar_permisos",
                               "leer_archivo", "listar_directorio", "buscar_archivos",
                               "buscar_contenido", "ejecutar_comando_seguro"],
        "Monitoreo":          ["info_sistema", "uso_disco", "uso_memoria",
                               "procesos_activos", "info_red", "paquetes_instalados"],
        "Memoria":            ["recordar_hecho", "ver_lo_que_recuerdo"],
        "Utilidades":         ["dia_de_la_semana"],
    }
    if PROXMOX_ENABLED:
        grupos["Proxmox"] = ["proxmox_nodos", "proxmox_vms", "proxmox_cluster", "proxmox_version"]
    lineas = []
    for grupo, nombres in grupos.items():
        lineas.append(f"  {grupo}: {', '.join(nombres)}")
    return "\n".join(lineas)


SYSTEM_PROMPT = f"""Eres Chatty, un asistente personal con acceso a herramientas del sistema. Reglas:
1. Tu nombre es CHATTY. Nunca digas que te llamas Qwen ni ningún otro nombre.
2. Responde ÚNICAMENTE en español. PROHIBIDO usar caracteres chinos, japoneses o coreanos.
3. Sé directo y conciso.
4. MEMORIA: Cuando el usuario comparta datos personales (nombre, trabajo, ciudad, estudios,
   preferencias, etc.), llama INMEDIATAMENTE a `recordar_hecho`. Hazlo de forma silenciosa.
5. FECHAS: Para calcular el día de la semana, SIEMPRE usa la tool `dia_de_la_semana`.
6. SISTEMA: Puedes consultar archivos, procesos, disco, memoria, red y más usando las tools
   de sistema. Úsalas cuando el usuario pregunte sobre su máquina o pida explorar archivos.
7. HERRAMIENTAS: Si el usuario pregunta qué puedes hacer o qué herramientas tienes, lista
   todas tus capacidades usando la siguiente información:
{_describir_tools()}"""

if __name__ == "__main__":
    mensajes_iniciales = cargar()

    sistema = SYSTEM_PROMPT
    contexto = "\n\n".join(filter(None, [contexto_resumenes(), contexto_semantico()]))
    if contexto:
        sistema += "\n\n" + contexto

    mensajes_iniciales = [SystemMessage(content=sistema)] + mensajes_iniciales
    state: State = {"messages": mensajes_iniciales}

    poderes = f"archivos · sistema · memoria"
    if PROXMOX_ENABLED:
        poderes += " · proxmox"
    print(f"Chatty [{poderes}]. Escribe 'salir' para terminar.\n")

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

        # Buscar contexto semántico solo si el mensaje es sustancioso
        ctx_sem = contexto_semantico(user) if len(user) >= 15 else ""
        if ctx_sem:
            state["messages"] = [
                m for m in state["messages"] if not isinstance(m, SystemMessage)
            ]
            state["messages"] = [SystemMessage(content=SYSTEM_PROMPT + "\n\n" + ctx_sem + "\n\n" + contexto_resumenes())] + state["messages"]

        n_antes = len(state["messages"])
        state["messages"].append(HumanMessage(content=user))
        state = app.invoke(state)
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and isinstance(last.content, str):
            print("🦂 Chatty:", last.content, "\n")
        guardar(state["messages"][n_antes:])
