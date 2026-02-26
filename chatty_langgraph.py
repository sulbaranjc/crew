from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
import os
import re
import inspect

from memory.episodica import cargar, guardar
from memory.semantica import guardar_hecho, cargar_hechos, como_contexto as contexto_semantico
from memory.resumenes import como_contexto as contexto_resumenes
from tools.sistema import SISTEMA_TOOLS
from tools.proxmox import PROXMOX_TOOLS, PROXMOX_ENABLED
from tools.ssh_pve import SSH_PVE_TOOLS, SSH_ENABLED as SSH_PVE_ENABLED, pve_explorar, pve_ups

MODEL = "qwen2.5:latest"
BASE_URL = "http://127.0.0.1:11434"


# ── Tools exclusivas de Chatty ────────────────────────────────────────────────

@tool
def ejecutar_en_laptop(comando: str) -> str:
    """Ejecuta un comando en la laptop del usuario. Permite operaciones de lectura Y escritura:
    mkdir, touch, cp, mv, rm (archivos), echo, git, python, etc.
    Ejemplos: 'mkdir ~/Descargas/temp', 'touch ~/notas.txt', 'mv ~/a.txt ~/b.txt'.
    Úsala cuando el usuario pida crear directorios, mover archivos, renombrar, etc."""
    import subprocess
    # Patrones de regex que bloquean comandos destructivos
    BLOQUEADOS_RE = [
        r"rm\s+-rf\s+[/~]\s*$",        # rm -rf / o rm -rf ~ (raíz o home entero)
        r"rm\s+-rf\s+/",               # rm -rf /cualquier-cosa-absoluta
        r":\(\)\{",                     # fork bomb
        r"\bmkfs\b", r"\bdd\b\s+if=",
        r"\bfdisk\b", r"\bparted\b",
        r"\breboot\b", r"\bshutdown\b", r"\bpoweroff\b",
        r"\bsudo\b", r"\bsu\s+-\b", r"\bpasswd\b", r"\bvisudo\b",
        r"curl\s*\|?\s*bash", r"wget\s*\|?\s*bash",
    ]
    for patron in BLOQUEADOS_RE:
        if re.search(patron, comando, re.IGNORECASE):
            return f"[Bloqueado] Operación no permitida (patrón: {patron})"
    try:
        r = subprocess.run(
            comando, shell=True, capture_output=True, text=True, timeout=15,
            cwd=os.path.expanduser("~"),
        )
        return r.stdout.strip() or r.stderr.strip() or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "[Error] El comando tardó demasiado."
    except Exception as e:
        return f"[Error] {e}"


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
    ejecutar_en_laptop,
    crear_archivo, eliminar_archivo, cambiar_permisos,
    recordar_hecho, ver_lo_que_recuerdo, dia_de_la_semana,
]

tools = CHATTY_TOOLS + SISTEMA_TOOLS + SSH_PVE_TOOLS

# Mapa nombre → objeto tool (para el interceptor)
_TOOLS_MAP: dict = {t.name: t for t in tools}
# Tools cuyo resultado no necesita re-invocación del LLM (solo guardan, no devuelven datos)
_TOOLS_SILENCIOSAS: set = {"recordar_hecho"}


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
        "Archivos y sistema": ["ejecutar_en_laptop", "crear_archivo", "eliminar_archivo", "cambiar_permisos",
                               "leer_archivo", "listar_directorio", "buscar_archivos",
                               "buscar_contenido", "ejecutar_comando_seguro"],
        "Monitoreo":          ["info_sistema", "uso_disco", "uso_memoria",
                               "procesos_activos", "info_red", "paquetes_instalados"],
        "Memoria":            ["recordar_hecho", "ver_lo_que_recuerdo"],
        "Utilidades":         ["dia_de_la_semana"],
    }
    if PROXMOX_ENABLED:
        grupos["Proxmox API"] = ["proxmox_nodos", "proxmox_vms", "proxmox_cluster", "proxmox_version"]
    if SSH_PVE_ENABLED:
        grupos["Proxmox SSH"] = ["pve_ejecutar", "pve_ups", "pve_version", "pve_vms",
                                  "pve_contenedores", "pve_almacenamiento", "pve_logs"]
    lineas = []
    for grupo, nombres in grupos.items():
        lineas.append(f"  {grupo}: {', '.join(nombres)}")
    return "\n".join(lineas)


SYSTEM_PROMPT = f"""Eres Chatty, un asistente personal con acceso a herramientas del sistema.

REGLA CRÍTICA: Cuando necesites información o realizar una acción, LLAMA A LA TOOL DIRECTAMENTE.
NUNCA pidas al usuario que ejecute comandos. NUNCA muestres código sh para que el usuario lo ejecute.
Tú tienes las herramientas — úsalas tú mismo sin preguntar permiso.

Reglas adicionales:
1. Tu nombre es CHATTY. Nunca digas que te llamas Qwen ni ningún otro nombre.
2. Responde ÚNICAMENTE en español. PROHIBIDO usar caracteres chinos, japoneses o coreanos.
3. Sé directo y conciso.
4. MEMORIA: Cuando el usuario comparta datos personales (nombre, trabajo, ciudad, estudios,
   preferencias, etc.), llama INMEDIATAMENTE a `recordar_hecho`. Hazlo de forma silenciosa.
5. FECHAS: Para calcular el día de la semana, SIEMPRE usa la tool `dia_de_la_semana`.
6. PROXMOX: Tienes acceso SSH directo al servidor Proxmox. Usa `pve_explorar` para exploración
   completa o `pve_ejecutar` para comandos específicos. EJECÚTALOS TÚ, no se los pidas al usuario.
7. HERRAMIENTAS FALTANTES: Si no puedes resolver algo con tus tools actuales, díselo y explica
   qué tool habría que programar.
8. Tus herramientas disponibles:
{_describir_tools()}"""

# ── Interceptor: detecta tool calls escritas como texto y las ejecuta ────────

def _interceptar_y_ejecutar(texto: str) -> tuple[str, dict[str, str]]:
    """
    Detecta y ejecuta en el texto del modelo:
    1. Llamadas a tools: -?tool_name("arg") o tool_name()
    2. Bloques bash/sh:  ```bash\\ncomando\\n```

    Devuelve (texto_limpio, {descripcion: resultado}).
    """
    ejecutados: dict[str, str] = {}
    texto_limpio = texto

    # ── 1. Tool calls escritas como texto ────────────────────────────────────
    if _TOOLS_MAP:
        nombres_re = "|".join(re.escape(n) for n in sorted(_TOOLS_MAP.keys(), key=len, reverse=True))
        patron_tool = re.compile(
            rf'-?({nombres_re})\s*\(\s*(?:"((?:[^"\\]|\\.)*)"\s*)?\)',
            re.MULTILINE | re.DOTALL,
        )
        for m in patron_tool.finditer(texto_limpio):
            nombre = m.group(1)
            arg_str = m.group(2)
            t = _TOOLS_MAP[nombre]
            try:
                if arg_str is None:
                    res = t.invoke({})
                else:
                    params = list(inspect.signature(t.func).parameters.keys())
                    res = t.invoke({params[0]: arg_str} if params else {})
            except Exception as e:
                res = f"[Error al ejecutar {nombre}: {e}]"
            ejecutados[nombre] = str(res)
        texto_limpio = patron_tool.sub("", texto_limpio).strip()

    # ── 2. Bloques ```bash / ```sh escritos como texto ────────────────────────
    patron_bash = re.compile(r'```(?:bash|sh)\n(.*?)\n```', re.DOTALL)
    for m in patron_bash.finditer(texto_limpio):
        cmd = m.group(1).strip()
        if not cmd:
            continue
        res = ejecutar_en_laptop.invoke({"comando": cmd})
        ejecutados[f"bash: {cmd[:40]}"] = str(res)
    texto_limpio = patron_bash.sub("", texto_limpio).strip()

    return texto_limpio, ejecutados


# ── Opción B: forzado de tools por keywords ──────────────────────────────────

_KW_EXPLORAR = [
    "explora", "explorar", "exploración",
    "investiga proxmox", "investigar proxmox",
    "qué tiene proxmox", "que tiene proxmox",
    "estado del proxmox", "estado de proxmox",
    "muéstrame proxmox", "muestrame proxmox",
    "ver proxmox", "revisa proxmox", "checa proxmox",
    "qué hay en proxmox", "que hay en proxmox",
]

_KW_UPS = [
    "ups", "sai", "batería del servidor", "bateria del servidor",
    "estado del ups", "estado del sai", "estado de la batería",
    "salicru", "carga batería", "carga bateria",
]


def _auto_pve(texto: str) -> str:
    """Pre-ejecuta tools SSH según keywords en el mensaje del usuario."""
    if not SSH_PVE_ENABLED:
        return ""
    t = texto.lower()
    if any(k in t for k in _KW_UPS):
        return pve_ups.invoke({})
    if any(k in t for k in _KW_EXPLORAR):
        return pve_explorar.invoke({})
    return ""


# ── API pública (usada por CLI y servidor web) ────────────────────────────────

def crear_estado_inicial() -> dict:
    """Inicializa el estado de conversación cargando historial y contexto."""
    mensajes = cargar()
    sistema = SYSTEM_PROMPT
    contexto = "\n\n".join(filter(None, [contexto_resumenes(), contexto_semantico()]))
    if contexto:
        sistema += "\n\n" + contexto
    return {"messages": [SystemMessage(content=sistema)] + mensajes}


def procesar_mensaje(user: str, state: dict) -> tuple[str, dict, list[str]]:
    """
    Procesa un mensaje del usuario.
    Devuelve (respuesta_final, nuevo_state, notificaciones).
    Las notificaciones son strings informativos (tools silenciosas, pre-ejecuciones).
    """
    notificaciones: list[str] = []

    # Actualizar contexto semántico si el mensaje es sustancioso
    ctx_sem = contexto_semantico(user) if len(user) >= 15 else ""
    if ctx_sem:
        state["messages"] = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
        state["messages"] = [SystemMessage(content=SYSTEM_PROMPT + "\n\n" + ctx_sem + "\n\n" + contexto_resumenes())] + state["messages"]

    n_antes = len(state["messages"])

    # Pre-ejecución por keywords (Proxmox / UPS)
    pve_ctx = _auto_pve(user)
    if pve_ctx:
        notificaciones.append("🔧 Proxmox explorado automáticamente.")
        msg = f"[Datos de Proxmox obtenidos automáticamente]:\n{pve_ctx}\n\nInstrucción del usuario: {user}"
    else:
        msg = user
    state["messages"].append(HumanMessage(content=msg))

    state = app.invoke(state)
    last = state["messages"][-1]
    respuesta_final = ""

    if isinstance(last, AIMessage) and isinstance(last.content, str):
        texto_limpio, ejecutados = _interceptar_y_ejecutar(last.content)

        if ejecutados:
            silenciosas = {k: v for k, v in ejecutados.items() if k in _TOOLS_SILENCIOSAS}
            con_datos   = {k: v for k, v in ejecutados.items() if k not in _TOOLS_SILENCIOSAS}

            for nombre in silenciosas:
                notificaciones.append(f"💾 [{nombre}] guardado en memoria.")

            if con_datos:
                ctx = "\n".join(f"[Resultado de {k}]:\n{v}" for k, v in con_datos.items())
                msgs_reinvoke = state["messages"] + [
                    HumanMessage(content=f"[Datos obtenidos automáticamente]:\n{ctx}\n\nPresenta estos resultados al usuario de forma clara y en español.")
                ]
                reinvocado = llm.invoke(msgs_reinvoke)
                respuesta_final = reinvocado.content if isinstance(reinvocado.content, str) else texto_limpio
                state["messages"].append(AIMessage(content=respuesta_final))
            else:
                respuesta_final = texto_limpio or "Hecho."
                state["messages"][-1] = AIMessage(content=respuesta_final)
        else:
            respuesta_final = last.content

    guardar(state["messages"][n_antes:])
    return respuesta_final, state, notificaciones


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Chatty — asistente local")
    parser.add_argument("--web", action="store_true", help="Lanzar interfaz web en http://localhost:8000")
    parser.add_argument("--port", type=int, default=8000, help="Puerto para el servidor web")
    args = parser.parse_args()

    if args.web:
        import uvicorn
        from server import app as web_app
        print(f"🌐 Chatty Web → http://localhost:{args.port}")
        uvicorn.run(web_app, host="0.0.0.0", port=args.port)
    else:
        # ── Modo CLI ─────────────────────────────────────────────────────────
        state = crear_estado_inicial()

        poderes = "archivos · sistema · memoria"
        if PROXMOX_ENABLED:
            poderes += " · proxmox"
        if SSH_PVE_ENABLED:
            poderes += " · pve-ssh"
        print(f"Chatty [{poderes}]. Escribe 'salir' para terminar.\n")

        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                print("👨 Tú:", m.content)
            elif isinstance(m, AIMessage) and isinstance(m.content, str):
                print("🦂 Chatty:", m.content)
        if len(state["messages"]) > 1:
            print()

        while True:
            user = input("👨 Tú: ").strip()
            if user.lower() in {"salir", "exit", "quit"}:
                break

            respuesta, state, notifs = procesar_mensaje(user, state)
            for n in notifs:
                print(n)
            print("🦂 Chatty:", respuesta, "\n")
