from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TextContent(BaseModel):
    text: str = Field(..., description="Normalized text content")
    original_format: Optional[str] = Field(default="text", description="Original source format")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)

