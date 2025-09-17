from __future__ import annotations
import hmac
import hashlib
from typing import Optional

from ..models.result import Result
from ..models.content import TextContent
from ..models.context import EventContext
from ..models.events import JanusEvent
from ..utils.ids import new_id, utc_now


class WebhookAdapter:
    def __init__(self, secret: str):
        self.secret = secret.encode()

    @property
    def source_type(self) -> str:
        return "webhook"

    def _verify(self, payload: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        mac = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        # Constant-time comparison
        return hmac.compare_digest(mac, signature)

    async def process_input(
        self, payload: bytes, signature: Optional[str], user_id: Optional[str], session_id: Optional[str]
    ) -> Result[JanusEvent, str]:
        if not self._verify(payload, signature):
            return Result.fail("invalid_signature")
        try:
            # MVP: treat full payload as text; real adapter would parse specific provider schema
            text = payload.decode("utf-8", errors="replace")
            content = TextContent(text=text, original_format="webhook", metadata={})
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

