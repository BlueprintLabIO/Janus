# Janus

Build your own AI teammate that truly understands your projects, people, and conversations. Self-hostable and extensible.

Micro-service architecture

Modular and swappable memory, LLM. Kind of like a PC.

Event-driven system with proactiveness

Plugin system for input, output and tools

Tool calling module supports MCP

Support different LLM providers

traceable auditable

dual permission system

uv

ruff

fastapi

pydantic


feel free to disagree and justify your disagreement.

I'm leaning towards versioned adapters for cleaner code, especially since this is a Python project. 

single content per event (but would this lose context?)

I think aggressive normalisation. like for the mvp, whilst
ai models are pure text, we can make everything normalise
to text, but with optional support for audio streams in mind later.
images can still be supported. video will be much later.

Option B: Result/Either Pattern
  - Explicit error handling
  - Functional programming style
  - More verbose

Option C: Error Events
  - Errors are just another event type
  - Consistent with event-driven architecture
  - Easier to monitor and debug

Would option C lead to random error event handling logic everywhere? is this the same for option B?


Option B: Sync Core + Async Wrappers
  - Simpler for basic operations
  - Can add async wrappers later
  - Mixed paradigms
this allows some sync operations to be easily represented. unless I misunderstand and all async supports sync code inside too?

yes opiniated defaults, but still keep everything configurable. So overrides are allowed.


