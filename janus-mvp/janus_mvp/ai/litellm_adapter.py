from __future__ import annotations
from typing import Any, Dict, List

from .base import AIAdapter, AIMsg, AIResponse


class LiteLLMAdapter(AIAdapter):
    provider: str = "litellm"
    model: str = "gpt-4o-mini"

    def _import(self):
        try:
            import litellm  # type: ignore
            return litellm
        except Exception as e:  # pragma: no cover - import guard
            raise RuntimeError("litellm not installed. Install with: pip install litellm") from e

    async def generate(self, messages: List[AIMsg], **kwargs) -> AIResponse:
        litellm = self._import()
        # Convert messages
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        resp = await litellm.acompletion(model=self.model, messages=msgs, **kwargs)
        # Extract content; follow OpenAI-like schema
        choice = resp.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")
        return AIResponse(content=content, finish_reason=finish_reason, raw=resp)

