from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage


class SuperState(TypedDict):
    messages: List[BaseMessage]
    agent: Optional[str]          # "chat" | "proxmox" — qué agente manejó el turno
    tool_results: Optional[Dict[str, Any]]  # datos crudos de tools (para proxmox, etc.)
