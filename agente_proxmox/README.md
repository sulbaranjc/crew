# Agente Proxmox (Modo Observador)

## Estructura

- app/: código fuente principal
- data/: inventario y logs
- runbooks/: procedimientos

## Uso rápido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## Comandos esperados
- /status
- /inventory
- /report

## Seguridad
- Solo lectura (modo observador)
- Tokens y SSH restringidos
