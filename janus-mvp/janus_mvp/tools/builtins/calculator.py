from __future__ import annotations
from ..base import SimpleTool, ToolParameter


async def _calc(params):
    op = params.get("operation", "add")
    a = float(params.get("a", 0))
    b = float(params.get("b", 0))
    if op == "add":
        result = a + b
    elif op == "sub":
        result = a - b
    elif op == "mul":
        result = a * b
    elif op == "div":
        if b == 0:
            raise ValueError("Division by zero")
        result = a / b
    else:
        raise ValueError(f"Unknown operation: {op}")
    return {"operation": op, "a": a, "b": b, "result": result}


CalculatorTool = SimpleTool(
    name="calculator",
    description="Perform basic arithmetic operations",
    parameters=[
        ToolParameter(name="operation", type="string", description="add|sub|mul|div", required=True),
        ToolParameter(name="a", type="number", description="Left operand", required=True),
        ToolParameter(name="b", type="number", description="Right operand", required=True),
    ],
    func=_calc,
)

