# Interface Specifications

## Overview

This document defines the interface contracts between Janus components. These interfaces enable independent development, testing, and deployment while ensuring system integration works correctly.

## Interface Design Principles

### Type Safety
- All interfaces defined with Pydantic models for runtime validation
- Strict typing with mypy for compile-time verification
- JSON Schema generation for API documentation
- Version compatibility through schema evolution

### Event-Driven Contracts
- Components communicate via events, not direct calls
- Event schemas define the contract between publishers and subscribers
- Backward compatibility maintained through event versioning
- Clear separation between internal and external events

### Extensibility
- Interfaces designed for future enhancement without breaking changes
- Plugin interfaces allow adding new capabilities
- Configuration-driven behavior reduces code changes
- Clear deprecation paths for interface evolution

## Core Event Interfaces

See [interfaces/](../../interfaces/) directory for complete interface definitions.

### Base Event Structure
```python
# interfaces/events.py
class JanusEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    stream_id: str = Field(..., description="Groups related events")
    event_type: str = Field(..., description="Event type for routing")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str = Field(..., description="Distributed tracing ID")
    content: EventContent = Field(..., description="Event payload")
    context: EventContext = Field(..., description="Metadata and context")
```

### Content Type Interfaces
```python
# interfaces/content.py
class TextContent(BaseModel):
    text: str
    language: Optional[str] = "en"
    metadata: Dict[str, Any] = {}

class AudioContent(BaseModel):
    data: bytes
    format: Literal["wav", "mp3", "opus"]
    duration_ms: int
    sample_rate: int
    channels: int = 1

class VideoContent(BaseModel):
    data: bytes
    format: Literal["mp4", "webm", "avi"]
    duration_ms: int
    width: int
    height: int
    fps: int
```

## Component Interfaces

### Input Processing Interface
```python
# interfaces/input.py
class InputAdapter(ABC):
    @abstractmethod
    async def process_input(self, raw_input: Any) -> JanusEvent:
        """Convert raw input to standardized JanusEvent"""
        pass
    
    @abstractmethod
    async def validate_source(self, source_data: Any) -> bool:
        """Validate input source authentication"""
        pass

class InputProcessor(ABC):
    @abstractmethod
    async def normalize_event(self, adapter_output: AdapterOutput) -> JanusEvent:
        """Normalize adapter output to standard event format"""
        pass
```

### Orchestrator Interface
```python
# interfaces/orchestrator.py
class EventHandler(ABC):
    @abstractmethod
    async def handle_event(self, event: JanusEvent) -> Optional[JanusEvent]:
        """Process event and optionally return response event"""
        pass

class DecisionEngine(ABC):
    @abstractmethod
    async def classify_intent(self, content: str, context: EventContext) -> ClassifiedIntent:
        """Determine user intent from input"""
        pass
    
    @abstractmethod
    async def select_strategy(self, intent: ClassifiedIntent, context: EventContext) -> ProcessingStrategy:
        """Choose processing approach for the intent"""
        pass
```

### Memory Interface
```python
# interfaces/memory.py
class MemoryStore(ABC):
    @abstractmethod
    async def store(self, memory: MemoryObject) -> str:
        """Store memory and return memory ID"""
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, context: RetrievalContext) -> List[MemoryObject]:
        """Retrieve relevant memories for query"""
        pass

class LearningEngine(ABC):
    @abstractmethod
    async def process_interaction(self, interaction: InteractionRecord) -> List[LearningUpdate]:
        """Learn from interaction and return updates"""
        pass
```

### Tools Interface
```python
# interfaces/tools.py
class Tool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute tool with given parameters"""
        pass
    
    @abstractmethod
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate tool parameters before execution"""
        pass

class ToolRegistry(ABC):
    @abstractmethod
    async def register_tool(self, tool: Tool) -> None:
        """Register new tool for use"""
        pass
    
    @abstractmethod
    async def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        pass
```

### Output Interface
```python
# interfaces/output.py
class OutputFormatter(ABC):
    @abstractmethod
    async def format_response(self, response: GeneratedResponse, context: OutputContext) -> FormattedResponse:
        """Format response for specific output channel"""
        pass

class OutputDeliverer(ABC):
    @abstractmethod
    async def deliver(self, formatted_response: FormattedResponse) -> DeliveryResult:
        """Deliver formatted response to target channel"""
        pass
```

## Configuration Interfaces

### Component Configuration
```python
# interfaces/config.py
class ComponentConfig(BaseModel):
    component_name: str
    version: str
    enabled: bool = True
    config: Dict[str, Any] = {}

class JanusConfig(BaseModel):
    instance_id: str
    components: List[ComponentConfig]
    global_config: Dict[str, Any] = {}
```

### Plugin Interface
```python
# interfaces/plugins.py
class Plugin(ABC):
    name: str
    version: str
    dependencies: List[str] = []
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of plugin"""
        pass
```

## API Interfaces

### REST API
```python
# interfaces/api.py
class APIRequest(BaseModel):
    request_id: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    request_id: str
    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### WebSocket Interface
```python
# interfaces/websocket.py
class WebSocketMessage(BaseModel):
    message_id: str
    message_type: Literal["event", "command", "response"]
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WebSocketConnection(ABC):
    @abstractmethod
    async def send_message(self, message: WebSocketMessage) -> None:
        """Send message to WebSocket client"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: WebSocketMessage) -> None:
        """Handle incoming WebSocket message"""
        pass
```

## Data Model Interfaces

### User and Session Models
```python
# interfaces/models.py
class User(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    preferences: Dict[str, Any] = {}
    created_at: datetime
    last_active: datetime

class Session(BaseModel):
    session_id: str
    user_id: str
    session_type: Literal["chat", "meeting", "call"]
    participants: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    expires_at: Optional[datetime] = None
```

### Memory Models
```python
# interfaces/memory_models.py
class MemoryObject(BaseModel):
    memory_id: str
    memory_type: Literal["episodic", "semantic", "procedural"]
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    last_accessed: Optional[datetime] = None

class Conversation(BaseModel):
    conversation_id: str
    participants: List[str]
    messages: List[Message]
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
```

## Error Handling Interfaces

### Exception Models
```python
# interfaces/exceptions.py
class JanusException(Exception):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationError(JanusException):
    error_code: str = "VALIDATION_ERROR"
    field_errors: List[FieldError] = []

class ProcessingError(JanusException):
    error_code: str = "PROCESSING_ERROR"
    component: str
    retry_possible: bool = True
```

## Testing Interfaces

### Test Utilities
```python
# interfaces/testing.py
class TestEventBus(ABC):
    @abstractmethod
    async def publish_test_event(self, event: JanusEvent) -> None:
        """Publish event for testing"""
        pass
    
    @abstractmethod
    async def wait_for_event(self, event_type: str, timeout: float = 5.0) -> JanusEvent:
        """Wait for specific event type in tests"""
        pass

class MockComponent(ABC):
    @abstractmethod
    async def mock_response(self, input_event: JanusEvent) -> JanusEvent:
        """Generate mock response for testing"""
        pass
```

## Interface Evolution

### Versioning Strategy
```python
# interfaces/versioning.py
class InterfaceVersion(BaseModel):
    major: int
    minor: int
    patch: int
    
    def is_compatible(self, other: 'InterfaceVersion') -> bool:
        """Check if versions are compatible"""
        return self.major == other.major and self.minor >= other.minor

class VersionedInterface(BaseModel):
    interface_name: str
    version: InterfaceVersion
    schema: Dict[str, Any]
    deprecated_at: Optional[datetime] = None
    removal_date: Optional[datetime] = None
```

### Migration Support
```python
# interfaces/migration.py
class InterfaceMigration(ABC):
    @abstractmethod
    async def migrate_up(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate data to newer interface version"""
        pass
    
    @abstractmethod
    async def migrate_down(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate data to older interface version"""
        pass
```

## Implementation Guidelines

### Interface Implementation
1. **Start with Pydantic models** for all data structures
2. **Use ABC (Abstract Base Classes)** for behavioral contracts
3. **Include comprehensive docstrings** with examples
4. **Validate all inputs** at interface boundaries
5. **Handle errors gracefully** with proper exception types

### Testing Requirements
1. **Unit tests** for all interface implementations
2. **Integration tests** for interface compatibility
3. **Contract tests** to verify interface compliance
4. **Performance tests** for interface overhead
5. **Migration tests** for interface evolution

### Documentation Standards
1. **API documentation** generated from interface definitions
2. **Example implementations** for each interface
3. **Migration guides** for interface changes
4. **Best practices** for interface usage
5. **Troubleshooting guides** for common interface issues

All interface definitions are maintained in the `/interfaces` directory with comprehensive tests and documentation to ensure reliable component integration.