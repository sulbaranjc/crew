from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.orchestrator import orchestrator
from app.memory.store import cargar_historial, guardar_historial, contexto_semantico, contexto_resumenes
from app.graph.state import SuperState


AGENTE_LABELS = {
    "chat": "💬",
    "proxmox": "🖥️ [Proxmox]",
}


def main():
    print("Superagente iniciado. Escribe 'salir' para terminar.\n")

    mensajes = cargar_historial()

    # Inyectar contexto de memoria semántica y resúmenes como sistema
    contexto = "\n\n".join(filter(None, [contexto_resumenes(), contexto_semantico()]))
    if contexto:
        mensajes = [SystemMessage(content=contexto)] + mensajes

    state: SuperState = {
        "messages": mensajes,
        "agent": None,
        "tool_results": None,
    }

    if state["messages"]:
        print("Historial cargado.\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSaliendo.")
            break

        if user_input.lower() in {"salir", "exit", "quit"}:
            print("Saliendo.")
            break

        if not user_input:
            continue

        state["messages"] = state["messages"] + [HumanMessage(content=user_input)]
        state["agent"] = None
        state["tool_results"] = None

        state = orchestrator.invoke(state)

        label = AGENTE_LABELS.get(state.get("agent", "chat"), "")
        last_msg = state["messages"][-1].content
        print(f"Agente {label}: {last_msg}\n")

        guardar_historial(state["messages"])


if __name__ == "__main__":
    main()
