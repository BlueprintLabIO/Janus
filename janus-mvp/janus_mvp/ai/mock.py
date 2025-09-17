from __future__ import annotations
from typing import List

from .base import AIAdapter, AIMsg, AIResponse


class MockAIAdapter(AIAdapter):
    provider: str = "mock"
    model: str = "mock-001"

    async def generate(self, messages: List[AIMsg], **kwargs) -> AIResponse:
        # Simple rule: mirror the last user message with polite prefix
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "" )
        return AIResponse(content=f"I understand you're saying: '{last_user}'. How else can I help?", finish_reason="stop")

