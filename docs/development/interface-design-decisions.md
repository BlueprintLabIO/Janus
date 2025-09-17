# Interface Design Decisions

This document records the key architectural decisions made for Janus interface design. These decisions drive the concrete implementation of all component interfaces.

## Decision Summary

| Decision Area | Choice | Justification |
|---------------|--------|---------------|
| Content Normalization | Aggressive text normalization | MVP simplicity, AI models are text-first |
| Event Granularity | Single content per event + references | Simplicity with context preservation |
| Interface Evolution | Single evolving interfaces | Python's dynamic nature, avoid version explosion |
| Error Handling | Result pattern + error events | Explicit local errors, system-level event errors |
| Async Strategy | Async-first throughout | AI operations are I/O bound, event-driven architecture |
| Configuration | Opinionated defaults with overrides | Easy MVP setup, full customization available |

## Detailed Decisions

### 1. Content Normalization: Aggressive Text Normalization

**Decision**: Input adapters must normalize all content to text + structured metadata.

**Justification**:
- **MVP Focus**: Current AI models (GPT-4, Claude) are primarily text-based
- **Simplicity**: Single content type reduces downstream processing complexity
- **Future-Proof**: Audio/video can be added later without breaking existing interfaces
- **Structured Metadata**: Rich information preserved in metadata for specialized processing

**Implementation**:
```python
class TextContent:
    text: str                    # Required normalized text
    original_format: str         # PDF, HTML, Slack message, etc.
    metadata: Dict[str, Any]     # Format-specific data
    extracted_entities: Dict     # Pre-extracted entities
```

**Examples**:
- PDF → extracted text + page numbers in metadata
- HTML → markdown text + link URLs in metadata  
- Image → OCR text + image description in metadata
- Slack message → plain text + emoji codes, mentions in metadata

### 2. Event Granularity: Single Content Per Event

**Decision**: Each event carries one primary content object with optional attachment references.

**Justification**:
- **Processing Simplicity**: Components handle one content type at a time
- **Event Routing**: Clear routing based on content type
- **Context Preservation**: Related content linked via event references
- **Parallel Processing**: Different content types can be processed concurrently

**Implementation**:
```python
class JanusEvent:
    content: TextContent                    # Primary content
    attachments: List[AttachmentRef] = []   # References to related content
    related_events: List[str] = []          # IDs of related events
    thread_id: Optional[str] = None         # Conversation threading
```

**Multi-content handling**:
- Slack message with image → 2 events (text + image) with same `thread_id`
- Email with attachments → N+1 events (email text + each attachment) linked via `related_events`

### 3. Interface Evolution: Single Evolving Interfaces

**Decision**: Use single interfaces with capability detection rather than versioned interfaces.

**Justification**:
- **Python Advantages**: Dynamic typing and duck typing make evolution easier
- **Maintenance**: Avoids exponential growth of versioned adapters (`SlackAdapterV1`, `SlackAdapterV2`, etc.)
- **Runtime Flexibility**: Components can declare capabilities and gracefully degrade
- **Migration Path**: New features added as optional fields with sensible defaults

**Implementation**:
```python
class InputAdapter(ABC):
    @property
    def supported_features(self) -> List[str]:
        """Runtime capability detection"""
        return ["text", "metadata", "threading"]
    
    @property  
    def api_version(self) -> str:
        """For compatibility checks"""
        return "1.0"
    
    async def process_input(self, raw_input: Any) -> Result[JanusEvent, ProcessingError]:
        # Implementation evolves while maintaining interface compatibility
```

**Evolution strategy**:
- Add optional parameters with defaults
- Mark deprecated features in docstrings
- Use capability detection for optional features
- Remove deprecated features only in major versions

### 4. Error Handling: Hybrid Result Pattern + Error Events

**Decision**: Use Result pattern for direct component interactions, error events for system-level failures.

**Justification**:
- **Explicit Local Errors**: Components must handle expected failures explicitly
- **Event System Consistency**: System failures flow through event system for monitoring
- **No Scattered Logic**: Error handling logic stays close to the operation
- **Observability**: All errors captured in event system for debugging

**Implementation**:
```python
# Result pattern for component calls
class Result[T, E]:
    value: Optional[T]
    error: Optional[E]
    
    @property
    def is_success(self) -> bool:
        return self.error is None

# Error events for system failures  
class ErrorEvent(JanusEvent):
    error_type: str
    component: str
    recoverable: bool
    context: Dict[str, Any]
```

**Error categories**:
- **Expected failures**: Return `Result` with error (validation, timeout, auth)
- **Unexpected failures**: Publish error event + graceful degradation (component crash, external service down)
- **Critical failures**: Error event + system shutdown (database unreachable, config corruption)

### 5. Async Strategy: Async-First Throughout

**Decision**: All interfaces are async by default.

**Justification**:
- **AI Workloads**: LLM API calls, vector searches, memory lookups are I/O bound
- **Event-Driven**: Natural fit for async event processing
- **Scalability**: Non-blocking operations essential for handling multiple conversations
- **Implementation Flexibility**: Easy to call sync code from async, hard to do reverse safely

**Implementation**:
```python
# All component interfaces are async
class InputAdapter(ABC):
    async def process_input(self, raw_input: Any) -> Result[JanusEvent, ProcessingError]:
        pass

# Sync operations wrapped when needed
async def process_text(text: str) -> str:
    return await asyncio.to_thread(sync_text_operation, text)
```

**Sync interop**:
- Call sync functions via `asyncio.to_thread()` for CPU-bound work
- Provide sync convenience wrappers for simple use cases if needed
- Never force async components to become sync

### 6. Configuration: Opinionated Defaults with Full Override

**Decision**: Strong default configurations with layered override system.

**Justification**:
- **MVP Velocity**: Zero-config startup for development
- **Production Ready**: Full customization available for production deployments
- **Maintenance**: Fewer configuration combinations to test and support
- **User Experience**: Works out of the box, customizable when needed

**Implementation**:
```python
# Configuration layering (priority order)
1. Hard-coded defaults (in code)
2. Default config files (bundled)
3. Environment variables  
4. User config files
5. Runtime overrides

# Example: LLM provider selection
defaults = {
    "llm_provider": "openai",
    "model": "gpt-4",
    "timeout": 30
}
```

**Override examples**:
- Development: Use defaults
- Production: Override via environment variables
- Power users: Custom config files
- Runtime: API calls to change settings

## Next Steps

With these foundational decisions made, we can now:

1. **Code the core interfaces** using these principles
2. **Implement MVP adapters** (Slack, webhook, API)
3. **Build event bus** with Result pattern error handling
4. **Create configuration system** with layered overrides

The interface design is now sufficiently specified to begin concrete implementation without major architectural changes.