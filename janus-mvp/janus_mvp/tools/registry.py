from __future__ import annotations
from typing import Dict, Optional, List

from .base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    async def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    async def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

