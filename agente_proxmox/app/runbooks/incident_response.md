# Runbook: Respuesta a Incidentes Proxmox

1. Identificar nodo/servicio afectado
2. Consultar logs recientes (`journalctl`, `systemctl --failed`)
3. Revisar recursos (CPU, RAM, disco)
4. Notificar a responsables
5. Documentar acciones en run_log.jsonl
