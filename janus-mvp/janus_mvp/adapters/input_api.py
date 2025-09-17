from __future__ import annotations
from typing import Any, Dict

from ..models.result import Result
from ..models.content import TextContent
from ..models.context import EventContext
from ..models.events import JanusEvent
from ..utils.ids import new_id, utc_now


class APIInputAdapter:
    @property
    def source_type(self) -> str:
        return "api"

    @property
    def supported_features(self) -> list[str]:
        return ["text", "metadata", "threading"]

    async def process_input(self, message: str, user_id: str | None, session_id: str | None) -> Result[JanusEvent, str]:
        try:
            content = TextContent(text=message, original_format="text", metadata={})
            ctx = EventContext(user_id=user_id, session_id=session_id, source=self.source_type)
            event = JanusEvent(
                event_id=new_id(),
                stream_id=session_id or user_id or new_id(),
                event_type="input.message.received",
                timestamp=utc_now(),
                trace_id=new_id(),
                content=content,
                context=ctx,
            )
            return Result.ok(event)
        except Exception as e:
            return Result.fail(str(e))

