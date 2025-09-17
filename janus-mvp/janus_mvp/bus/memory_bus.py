from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, List

from ..models.events import JanusEvent


Handler = Callable[[JanusEvent], Awaitable[None]]


class InMemoryEventBus:
    def __init__(self) -> None:
        self.subscribers: Dict[str, List[Handler]] = {}
        self.event_history: List[JanusEvent] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def publish(self, event: JanusEvent) -> None:
        self.event_history.append(event)
        handlers = self.subscribers.get(event.event_type, []) + self.subscribers.get("*", [])
        for handler in handlers:
            await handler(event)

