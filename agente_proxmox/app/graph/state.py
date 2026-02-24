from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage

class State(TypedDict):
    messages: List[BaseMessage]
    intent: Optional[str]                 # "consulta" | "accion"
    plan: Optional[List[Dict[str, Any]]]
    tool_results: Optional[Dict[str, Any]]
    risk: Optional[str]                   # "low" | "medium" | "high"
