from __future__ import annotations
from ..base import SimpleTool, ToolParameter


async def _echo(params):
    return {
        "echo": params.get("text", ""),
    }


EchoTool = SimpleTool(
    name="echo",
    description="Echo back the given text",
    parameters=[
        ToolParameter(name="text", type="string", description="Text to echo", required=True),
    ],
    func=_echo,
)

