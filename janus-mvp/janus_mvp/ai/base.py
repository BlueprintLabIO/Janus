from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AIMsg(BaseModel):
    role: str  # system|user|assistant|tool
    content: str


class AIResponse(BaseModel):
    content: str
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class AIAdapter(BaseModel):
    provider: str
    model: str

    async def generate(self, messages: List[AIMsg], **kwargs) -> AIResponse:  # pragma: no cover - interface
        raise NotImplementedError

