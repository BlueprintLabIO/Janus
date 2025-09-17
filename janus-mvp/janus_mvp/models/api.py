from __future__ import annotations
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    used_tools: List[str] = Field(default_factory=list)
    memory_refs: List[str] = Field(default_factory=list)
    trace_id: Optional[str] = None

