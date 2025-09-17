from __future__ import annotations
from typing import List

from ..bus.memory_bus import InMemoryEventBus
from ..ai.base import AIAdapter, AIMsg
from ..memory.store import InMemoryStore, MemoryItem
from ..models.events import JanusEvent
from ..models.result import Result
from ..tools.registry import ToolRegistry
from ..utils.ids import new_id, utc_now
from ..utils.logging import get_logger


log = get_logger("orchestrator")


class Orchestrator:
    def __init__(self, bus: InMemoryEventBus, tools: ToolRegistry, memory: InMemoryStore, ai: AIAdapter | None = None) -> None:
        self.bus = bus
        self.tools = tools
        self.memory = memory
        self.ai = ai
        self.bus.subscribe("input.message.received", self._on_input)

    async def _on_input(self, event: JanusEvent) -> None:
        # Store input to memory
        self.memory.add(
            MemoryItem(
                id=new_id(),
                user_id=event.context.user_id,
                session_id=event.context.session_id,
                text=f"User: {event.content.text}",
                timestamp=utc_now(),
            )
        )

        # Decision: simple pattern-based for MVP
        text = event.content.text.strip()
        response_text = await self._generate_response(text, event)

        # Store response to memory
        self.memory.add(
            MemoryItem(
                id=new_id(),
                user_id=event.context.user_id,
                session_id=event.context.session_id,
                text=f"Assistant: {response_text}",
                timestamp=utc_now(),
            )
        )

        # Publish response-ready event (not consumed further in MVP)
        # This shows event-driven flow without implementing delivery subscribers.
        await self.bus.publish(
            JanusEvent(
                event_id=new_id(),
                stream_id=event.stream_id,
                event_type="orchestrator.response.ready",
                timestamp=utc_now(),
                trace_id=event.trace_id,
                content=event.content.model_copy(update={"text": response_text}),
                context=event.context,
            )
        )

    async def _generate_response(self, text: str, event: JanusEvent) -> str:
        t = text.lower()
        used_tools: List[str] = []

        if any(k in t for k in ["hello", "hi", "hey"]):
            return "Hello! I'm Janus, your AI teammate. How can I help you today?"

        if "time" in t:
            tool = await self.tools.get_tool("time")
            if tool:
                used_tools.append("time")
                res = await tool.execute({})
                if res.success:
                    return f"I executed the time tool. Result: {res.result}"
                else:
                    return f"Tried to get time but failed: {res.error}"

        if "calculate" in t or any(op in t for op in ["add", "sum", "plus", "+", "-", "*", "/"]):
            # naive parse: look for numbers
            import re

            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", text)]
            op = "add"
            if "sub" in t or "minus" in t or "-" in t:
                op = "sub"
            if "mul" in t or "times" in t or "*" in t:
                op = "mul"
            if "div" in t or "divide" in t or "/" in t:
                op = "div"

            tool = await self.tools.get_tool("calculator")
            if tool and len(nums) >= 2:
                used_tools.append("calculator")
                res = await tool.execute({"operation": op, "a": nums[0], "b": nums[1]})
                if res.success:
                    return f"I executed the calculator tool. Result: {res.result}"
                else:
                    return f"Calculation failed: {res.error}"

        if t.startswith("remember "):
            fact = text[8:].strip()
            self.memory.add(
                MemoryItem(
                    id=new_id(),
                    user_id=event.context.user_id,
                    session_id=event.context.session_id,
                    text=f"Fact: {fact}",
                    timestamp=utc_now(),
                )
            )
            return f"Got it. I'll remember that: {fact}"

        if "what do you remember" in t or "what do you remember about me" in t:
            memories = self.memory.list_for_user(event.context.user_id or "")
            recent = [m.text for m in memories][-5:]
            if not recent:
                return "I don't have any specific memories yet."
            return "Here's what I remember from our recent interaction:\n" + "\n".join(recent)

        # AI generation fallback if adapter configured
        if self.ai:
            # Build short context from recent memory
            recent = self.memory.recent_for_session(event.context.session_id or "", limit=6)
            messages: list[AIMsg] = [
                AIMsg(role="system", content="You are Janus, a helpful AI teammate. Be concise and actionable."),
            ]
            for m in reversed(recent):
                if m.text.startswith("User: "):
                    messages.append(AIMsg(role="user", content=m.text[len("User: ") :]))
                elif m.text.startswith("Assistant: "):
                    messages.append(AIMsg(role="assistant", content=m.text[len("Assistant: ") :]))
            messages.append(AIMsg(role="user", content=text))
            try:
                resp = await self.ai.generate(messages)
                return resp.content or ""
            except Exception as e:
                log.warning("AI adapter failed: %s", e)

        # default reflection
        return f"Based on our conversation, I understand you're asking about: {text}"
