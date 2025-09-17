# Event-Driven Architecture

## Overview

Janus uses an event-driven architecture as its foundational design pattern. This enables asynchronous processing, loose coupling between components, parallel execution of AI workloads, and natural support for real-time audio/video streams.

## Design Principles

### Event-First Thinking
- **All interactions are events**: User messages, tool completions, memory updates, responses
- **Components communicate via events**: No direct service-to-service calls
- **Async by default**: Operations are non-blocking and can be processed in parallel
- **Stream-oriented**: Designed for continuous streams of audio/video, not just discrete messages

### Loose Coupling
- **Components don't know about each other**: Services publish events without knowing who consumes them
- **Pluggable architecture**: Add new services by subscribing to relevant events
- **Independent scaling**: Each component scales based on its own load characteristics
- **Failure isolation**: Component failures don't cascade to other services

### Parallel Processing
- **Concurrent execution**: Memory retrieval, LLM processing, and tool execution happen simultaneously
- **Pipeline optimization**: Events flow through processing stages without blocking
- **Resource efficiency**: CPU and I/O operations overlap for better performance
- **Latency reduction**: Total response time is limited by slowest component, not sum of all components

## Core Event Architecture

### Event Structure
```python
class JanusEvent:
    event_id: str           # Unique identifier for tracing
    stream_id: str          # Groups related events (conversation/session)
    event_type: str         # Category of event for routing
    timestamp: datetime     # When event occurred
    content: EventContent   # Payload (text, audio, video, etc.)
    context: EventContext   # Metadata about source, user, session
    trace_id: str          # For distributed tracing
    correlation_id: str    # Links events in same request flow
```

### Event Types
```python
# Input Events (from external sources)
class TextMessageEvent(JanusEvent):
    content: TextContent

class AudioChunkEvent(JanusEvent):
    content: AudioContent

class VideoFrameEvent(JanusEvent):
    content: VideoContent

class ToolResultEvent(JanusEvent):
    content: ToolResult

# Processing Events (internal)
class IntentClassifiedEvent(JanusEvent):
    content: ClassifiedIntent

class ContextAssembledEvent(JanusEvent):
    content: AssembledContext

class ResponseGeneratedEvent(JanusEvent):
    content: GeneratedResponse

# Output Events (for delivery)
class ResponseReadyEvent(JanusEvent):
    content: FormattedResponse

class ProactiveSuggestionEvent(JanusEvent):
    content: ProactiveSuggestion
```

### Event Flow Patterns

#### Linear Flow (Simple Request-Response)
```
User Message → Intent Classification → Context Assembly → LLM Processing → Response Delivery
```

#### Parallel Flow (Optimized Processing)
```
User Message → [Intent Classification, Context Assembly, Tool Preparation] → LLM Processing → Response Delivery
```

#### Stream Flow (Real-time Audio)
```
Audio Stream → Audio Chunks → [Voice Activity Detection, Transcription Buffer] → Complete Utterance → Text Processing Flow
```

#### Reactive Flow (Proactive Features)
```
Any Event → Pattern Detection → Proactive Suggestion → User Notification
```

## Component Event Contracts

### Input Processing
**Subscribes to**: None (entry point)
**Publishes**:
- `input.message.received` - Text message from any channel
- `input.audio.chunk` - Audio data chunk from voice input
- `input.video.frame` - Video frame from video input
- `input.stream.started` - New conversation/session began
- `input.stream.ended` - Conversation/session completed

### Orchestrator (Conductor)
**Subscribes to**:
- `input.*` - All input events for processing coordination
- `memory.context.assembled` - Context retrieval completed
- `tools.execution.completed` - Tool execution finished
- `llm.response.generated` - LLM processing completed

**Publishes**:
- `orchestrator.intent.classified` - User intent determined
- `orchestrator.context.requested` - Context retrieval needed
- `orchestrator.tools.requested` - Tool execution needed
- `orchestrator.llm.requested` - LLM processing needed
- `orchestrator.response.ready` - Final response prepared

### Memory System
**Subscribes to**:
- `input.*` - All input events for storage
- `orchestrator.context.requested` - Context retrieval requests
- `tools.execution.completed` - Tool results for learning
- `llm.response.generated` - Responses for conversation history

**Publishes**:
- `memory.context.assembled` - Retrieved context for request
- `memory.pattern.detected` - Learned pattern identified
- `memory.conflict.detected` - Contradictory information found
- `memory.consolidation.completed` - Memory cleanup finished

### Tools System
**Subscribes to**:
- `orchestrator.tools.requested` - Tool execution requests

**Publishes**:
- `tools.execution.started` - Tool execution began
- `tools.execution.completed` - Tool execution finished
- `tools.execution.failed` - Tool execution failed
- `tools.execution.progress` - Long-running tool progress update

### Output Processing
**Subscribes to**:
- `orchestrator.response.ready` - Responses ready for delivery
- `proactive.suggestion.ready` - Proactive suggestions for delivery

**Publishes**:
- `output.message.sent` - Message delivered successfully
- `output.message.failed` - Message delivery failed
- `output.formatting.completed` - Response formatted for channel

### Proactive Intelligence
**Subscribes to**:
- `*` - All events for pattern detection
- `memory.pattern.detected` - Learned patterns from memory

**Publishes**:
- `proactive.suggestion.ready` - Proactive suggestion generated
- `proactive.pattern.detected` - Real-time pattern identified
- `proactive.intervention.needed` - User assistance recommended

## Event Bus Implementation

### MVP: In-Memory Event Bus
```python
class InMemoryEventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[JanusEvent] = []
    
    async def publish(self, event: JanusEvent):
        # Store for debugging/replay
        self.event_history.append(event)
        
        # Notify all subscribers
        pattern_subscribers = self.subscribers.get(event.event_type, [])
        wildcard_subscribers = self.subscribers.get('*', [])
        
        for subscriber in pattern_subscribers + wildcard_subscribers:
            await subscriber(event)
    
    def subscribe(self, event_pattern: str, handler: Callable):
        if event_pattern not in self.subscribers:
            self.subscribers[event_pattern] = []
        self.subscribers[event_pattern].append(handler)
```

### Production: Redis Streams
```python
class RedisEventBus:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.consumer_groups = {}
    
    async def publish(self, event: JanusEvent):
        stream_name = f"janus:{event.event_type}"
        await self.redis.xadd(stream_name, event.model_dump())
    
    async def subscribe(self, event_pattern: str, handler: Callable):
        # Create consumer group for load balancing
        group_name = f"janus_{event_pattern}_processors"
        consumer_name = f"worker_{uuid.uuid4()}"
        
        # Process events from stream
        while True:
            messages = await self.redis.xreadgroup(
                group_name, consumer_name, 
                {f"janus:{event_pattern}": ">"}, 
                count=1, block=1000
            )
            
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    event = JanusEvent.model_validate(fields)
                    await handler(event)
                    await self.redis.xack(stream, group_name, msg_id)
```

## Session and Stream Management

### Session Concept
```python
class ActiveSession:
    session_id: str
    session_type: Literal["chat", "meeting", "call"]
    participants: List[Participant]
    state: SessionState
    working_memory: Dict[str, Any]
    event_buffer: List[JanusEvent]
    created_at: datetime
    last_activity: datetime
```

### Stream Processing
```python
class StreamProcessor:
    def __init__(self):
        self.active_sessions: Dict[str, ActiveSession] = {}
        self.event_buffers: Dict[str, EventBuffer] = {}
    
    async def process_event(self, event: JanusEvent):
        # Get or create session
        session = await self.get_or_create_session(event.stream_id)
        
        # Add to event buffer for stream processing
        buffer = self.event_buffers[event.stream_id]
        await buffer.add_event(event)
        
        # Process based on event type and session state
        if event.event_type == "audio_chunk":
            await self.process_audio_stream(event, session)
        elif event.event_type == "text_message":
            await self.process_text_message(event, session)
```

## Error Handling and Resilience

### Event Retry Logic
```python
class ResilientEventProcessor:
    async def handle_event(self, event: JanusEvent):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.process_event(event)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    # Send to dead letter queue
                    await self.dead_letter_queue.send(event, error=e)
                else:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
```

### Circuit Breaker Pattern
```python
class CircuitBreakerEventHandler:
    def __init__(self):
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_threshold = 5
    
    async def handle_event(self, event: JanusEvent):
        if self.state == "OPEN":
            # Circuit breaker open - fail fast
            raise ServiceUnavailableError("Circuit breaker open")
        
        try:
            await self.process_event(event)
            self.on_success()
        except Exception as e:
            self.on_failure()
            raise
```

## Observability in Event Systems

### Event Tracing
```python
class TracedEventBus:
    async def publish(self, event: JanusEvent):
        # Add tracing context
        span = tracer.start_span(f"event.{event.event_type}")
        span.set_attribute("event.id", event.event_id)
        span.set_attribute("stream.id", event.stream_id)
        
        try:
            await self.event_bus.publish(event)
        finally:
            span.end()
```

### Event Metrics
```python
class MetricsEventBus:
    def __init__(self):
        self.event_counter = Counter('janus_events_total', ['event_type', 'status'])
        self.event_duration = Histogram('janus_event_processing_seconds', ['event_type'])
    
    async def publish(self, event: JanusEvent):
        start_time = time.time()
        try:
            await self.event_bus.publish(event)
            self.event_counter.labels(event_type=event.event_type, status='success').inc()
        except Exception as e:
            self.event_counter.labels(event_type=event.event_type, status='error').inc()
            raise
        finally:
            duration = time.time() - start_time
            self.event_duration.labels(event_type=event.event_type).observe(duration)
```

## Testing Event-Driven Systems

### Event Test Harness
```python
class EventTestHarness:
    def __init__(self):
        self.event_bus = InMemoryEventBus()
        self.published_events: List[JanusEvent] = []
        self.event_bus.subscribe('*', self.capture_event)
    
    async def capture_event(self, event: JanusEvent):
        self.published_events.append(event)
    
    async def send_event_and_wait(self, event: JanusEvent, expected_event_type: str, timeout: float = 5.0):
        await self.event_bus.publish(event)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            for captured_event in self.published_events:
                if captured_event.event_type == expected_event_type:
                    return captured_event
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Expected event {expected_event_type} not received within {timeout}s")
```

### Integration Testing
```python
class EventIntegrationTest:
    async def test_complete_conversation_flow(self):
        harness = EventTestHarness()
        
        # Set up all components
        orchestrator = Orchestrator(harness.event_bus)
        memory = MemoryService(harness.event_bus)
        llm = LLMService(harness.event_bus)
        output = OutputService(harness.event_bus)
        
        # Send input event
        input_event = TextMessageEvent(
            stream_id="test_conversation",
            content=TextContent(text="Hello, can you help me?"),
            context=create_test_context()
        )
        
        # Verify complete flow
        response_event = await harness.send_event_and_wait(
            input_event, 
            "output.message.sent"
        )
        
        assert response_event.content.text != ""
        assert "help" in response_event.content.text.lower()
```

## Benefits for Janus

### Natural Fit for AI Workloads
- **Async LLM calls**: Don't block while waiting for AI responses
- **Parallel processing**: Memory retrieval and tool preparation happen simultaneously
- **Stream processing**: Audio/video streams processed as events arrive
- **Proactive behavior**: Background pattern detection triggers suggestions

### Extensibility
- **Add new input channels**: Create new event publishers without changing core logic
- **Add new capabilities**: Subscribe to existing events to add features
- **Replace components**: Swap implementations without affecting other services
- **A/B testing**: Route events to different processors for comparison

### Production Readiness
- **Monitoring**: Rich event metrics and tracing for observability
- **Reliability**: Circuit breakers and retry logic for resilience
- **Scaling**: Components scale independently based on event load
- **Debugging**: Event history provides audit trail for troubleshooting

The event-driven architecture provides the foundation for building a responsive, extensible, and maintainable AI teammate that can handle real-time interactions while maintaining system reliability and performance.