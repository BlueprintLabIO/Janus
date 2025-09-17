from __future__ import annotations
from typing import Any, Dict, Callable, Awaitable, Optional, List
from pydantic import BaseModel


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class ToolResult(BaseModel):
    name: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class Tool(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter] = []

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:  # pragma: no cover - interface
        raise NotImplementedError


class SimpleTool(Tool):
    func: Callable[[Dict[str, Any]], Awaitable[Any]]

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            result = await self.func(parameters)
            return ToolResult(name=self.name, success=True, result=result)
        except Exception as e:  # simplify for MVP
            return ToolResult(name=self.name, success=False, error=str(e))

