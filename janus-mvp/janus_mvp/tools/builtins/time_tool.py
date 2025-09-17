from __future__ import annotations
from datetime import datetime, timezone
from ..base import SimpleTool, ToolParameter


async def _time(params):
    fmt = params.get("format", "%Y-%m-%d %H:%M:%S %Z")
    now = datetime.now(timezone.utc)
    return {
        "current_time": now.strftime(fmt),
        "iso": now.isoformat(),
        "epoch": int(now.timestamp()),
        "timezone": "UTC",
    }


TimeTool = SimpleTool(
    name="time",
    description="Get the current time",
    parameters=[
        ToolParameter(name="format", type="string", description="strftime format", required=False, default="%Y-%m-%d %H:%M:%S %Z"),
    ],
    func=_time,
)

