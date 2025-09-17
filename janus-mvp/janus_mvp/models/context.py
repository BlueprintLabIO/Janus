from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EventContext(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = "api"
    permissions: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)

