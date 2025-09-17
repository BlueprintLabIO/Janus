from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .content import TextContent
from .context import EventContext


class JanusEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    stream_id: str = Field(..., description="Conversation/session grouping")
    event_type: str = Field(..., description="Event routing type")
    timestamp: datetime = Field(...)
    trace_id: str = Field(...)
    content: TextContent = Field(...)
    context: EventContext = Field(default_factory=EventContext)


class ErrorEvent(JanusEvent):
    error_type: str
    component: str
    recoverable: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)

