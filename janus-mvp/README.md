# Janus MVP

A minimal, event-driven AI teammate scaffold aligned with the repository's architecture and interface principles.

## Quick Start

- Change directory: `cd janus-mvp`
- Install dependencies: `pip install -r requirements.txt`
- Start API server: `python main.py`
- Try chat endpoint: `python example_client.py` or `python example_client.py interactive`
- API docs: open `http://localhost:8000/docs`

## What’s Included

- Async-first FastAPI server (`/chat`, `/tools`, `/memory/{user_id}`, `/health`)
- In-memory event bus with publish/subscribe
- Result pattern for input normalization
- Single-content events with aggressive text normalization
- Simple orchestrator with pattern-based decisions
- In-memory memory store with basic search and listing
- Tool framework + built-ins: echo, time, calculator

## Structure

- `main.py` – runs the server (Uvicorn)
- `janus_mvp/server/api.py` – API and wiring
- `janus_mvp/orchestrator/core.py` – core request handling
- `janus_mvp/bus/memory_bus.py` – in-memory event bus
- `janus_mvp/memory/store.py` – in-memory memory store
- `janus_mvp/models/*` – pydantic models and result type
- `janus_mvp/tools/*` – tool base + registry + built-ins
- `example_client.py` – quick demo client

## Notes

- This MVP is intentionally simple (no external LLM). It demonstrates the event-driven architecture, interface contracts, and extensibility points described in `docs/overview` and `docs/development`.
- AI adapter layer added. By default, uses a mock adapter. To enable a generic provider via LiteLLM, set `JANUS_AI_PROVIDER=litellm` and `JANUS_MODEL=gpt-4o-mini` (or any supported model) and install `litellm`.
- Install optional AI dependency: `pip install litellm` and set provider-specific API keys (e.g., `OPENAI_API_KEY`).
