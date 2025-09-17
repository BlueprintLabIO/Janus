from __future__ import annotations
import os
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

from ..adapters.input_api import APIInputAdapter
from ..adapters.webhook import WebhookAdapter
from ..bus.memory_bus import InMemoryEventBus
from ..memory.store import InMemoryStore
from ..models.api import ChatRequest, ChatResponse
from ..models.events import JanusEvent
from ..tools.registry import ToolRegistry
from ..tools.builtins.echo import EchoTool
from ..tools.builtins.time_tool import TimeTool
from ..tools.builtins.calculator import CalculatorTool
from ..orchestrator.core import Orchestrator
from ..ai.mock import MockAIAdapter
from ..ai.litellm_adapter import LiteLLMAdapter
from ..utils.ids import new_id, utc_now


def create_app() -> FastAPI:
    app = FastAPI(title="Janus MVP", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core components
    bus = InMemoryEventBus()
    memory = InMemoryStore()
    tools = ToolRegistry()

    # Register built-in tools
    # Note: register_tool is async; use simple startup event to register
    # AI adapter selection via env
    ai_provider = os.getenv("JANUS_AI_PROVIDER", "mock").lower()
    ai_model = os.getenv("JANUS_MODEL", "gpt-4o-mini")
    ai = None
    if ai_provider == "litellm":
        ai = LiteLLMAdapter(model=ai_model)
    else:
        ai = MockAIAdapter()

    orchestrator = Orchestrator(bus=bus, tools=tools, memory=memory, ai=ai)
    adapter = APIInputAdapter()
    webhook = WebhookAdapter(secret=os.getenv("JANUS_WEBHOOK_SECRET", "dev_secret"))

    @app.on_event("startup")
    async def _startup():
        await tools.register_tool(EchoTool)
        await tools.register_tool(TimeTool)
        await tools.register_tool(CalculatorTool)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/tools")
    async def list_tools():
        ts = await tools.list_tools()
        return [{"name": t.name, "description": t.description, "parameters": [p.model_dump() for p in t.parameters]} for t in ts]

    @app.get("/memory/{user_id}")
    async def get_memory(user_id: str):
        items = memory.list_for_user(user_id)
        return [{"id": i.id, "text": i.text, "timestamp": i.timestamp.isoformat()} for i in items]

    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        # Normalize to event
        evt_res = await adapter.process_input(req.message, req.user_id, req.session_id)
        if not evt_res.is_success:
            return ChatResponse(response=f"Invalid input: {evt_res.error}")
        event = evt_res.value  # type: ignore

        # Capture response via a temporary subscriber on response event
        response_text: str | None = None

        async def capture_response(e: JanusEvent) -> None:
            nonlocal response_text
            response_text = e.content.text

        bus.subscribe("orchestrator.response.ready", capture_response)

        # Publish input, let orchestrator process
        await bus.publish(event)

        # Since processing is immediate in-memory, response_text should be set
        text = response_text or "Unexpected error: no response generated"
        return ChatResponse(response=text, trace_id=event.trace_id)

    @app.post("/webhook")
    async def webhook_endpoint(request: Request, x_signature: str | None = Header(default=None), user_id: str | None = None, session_id: str | None = None):
        payload = await request.body()
        evt_res = await webhook.process_input(payload, x_signature, user_id, session_id)
        if not evt_res.is_success:
            return {"status": "error", "reason": evt_res.error}
        event = evt_res.value  # type: ignore

        response_text: str | None = None

        async def capture_response(e: JanusEvent) -> None:
            nonlocal response_text
            response_text = e.content.text

        bus.subscribe("orchestrator.response.ready", capture_response)
        await bus.publish(event)
        return {"status": "ok", "response": response_text, "trace_id": event.trace_id}

    return app
