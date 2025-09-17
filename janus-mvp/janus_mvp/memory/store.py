from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryItem:
    id: str
    user_id: Optional[str]
    session_id: Optional[str]
    text: str
    timestamp: datetime


class InMemoryStore:
    def __init__(self) -> None:
        self._items: List[MemoryItem] = []

    def add(self, item: MemoryItem) -> None:
        self._items.append(item)

    def list_for_user(self, user_id: str) -> List[MemoryItem]:
        return [i for i in self._items if i.user_id == user_id]

    def recent_for_session(self, session_id: str, limit: int = 10) -> List[MemoryItem]:
        items = [i for i in self._items if i.session_id == session_id]
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items[:limit]

    def search(self, user_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        results = [i for i in self._items if (i.user_id == user_id and query.lower() in i.text.lower())]
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

