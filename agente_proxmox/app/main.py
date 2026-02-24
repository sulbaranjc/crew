# Entry point CLI para el agente Proxmox

def main():
    print("Agente Proxmox iniciado. Usa comandos como /status, /inventory, /report.")
    while True:
        try:
            cmd = input("> ").strip()
            if cmd in ("exit", "quit", "salir"):
                print("Saliendo del agente.")
                break
            elif cmd == "/status":
                print("[Simulado] Estado del cluster: OK")
            elif cmd == "/inventory":
                print("[Simulado] Inventario: nodo1, nodo2, nodo3")
            elif cmd == "/report":
                print("[Simulado] Reporte generado.")
            elif cmd:
                print(f"Comando no reconocido: {cmd}")
        except (KeyboardInterrupt, EOFError):
            print("\nSaliendo del agente.")
            break

if __name__ == "__main__":
    main()
