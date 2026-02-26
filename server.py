"""Servidor web de Chatty — FastAPI + WebSocket.
Arranca con: python chatty_langgraph.py --web
"""

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Importar la lógica de Chatty
from chatty_langgraph import crear_estado_inicial, procesar_mensaje

app = FastAPI(title="Chatty")

# Servir archivos estáticos
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    await ws.accept()

    # Estado de conversación independiente por conexión
    state = crear_estado_inicial()

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            user = payload.get("message", "").strip()
            if not user:
                continue

            # Notificar que está pensando
            await ws.send_text(json.dumps({"type": "thinking"}))

            # Procesar (operación bloqueante — en hilo separado para no bloquear el loop)
            import asyncio
            loop = asyncio.get_event_loop()
            respuesta, state, notifs = await loop.run_in_executor(
                None, procesar_mensaje, user, state
            )

            # Enviar notificaciones de tools
            for n in notifs:
                await ws.send_text(json.dumps({"type": "tool", "content": n}))

            # Enviar respuesta final
            await ws.send_text(json.dumps({"type": "message", "content": respuesta}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "content": str(e)}))
