# Janus Scaling Architecture

## Scaling Strategy: Multi-Tenant Service Pools (Not Per-User Instances)

### ❌ Avoid: 1:1 User-to-Instance Model
```
User A ←→ Janus Instance #1 (wasteful)
User B ←→ Janus Instance #2 (isolated)
User C ←→ Janus Instance #3 (expensive)
```

**Problems:**
- Memory isolation prevents cross-user learning
- Redundant resource usage (LLM pools, tool registries)
- Expensive scaling (new instance per user)
- No system-wide insights

### ✅ Recommended: Microservice Pool Architecture

```
┌─ Input Layer (Horizontally Scaled) ─┐
│  Stateless input processors         │
│  Handle all sources for all users   │
└──────────────────────────────────────┘
           │ user_id routing
┌─ Event Bus (Distributed) ─┐
│  Redis/Kafka partitioned  │
│  by user_id               │
└───────────────────────────┘
           │
┌─ Processing Pools ─┐
│  Orchestrators     │
│  Memory Services   │  ← User-partitioned data
│  Tool Executors    │  ← Shared tool pools
└────────────────────┘
           │
┌─ Output Layer ─┐
│  Multi-channel │
│  deliverers    │
└────────────────┘
```

## Real-World Input Reality

**One user = 20+ concurrent input streams:**
- Slack DMs + channels
- Email + calendar
- GitHub notifications
- API integrations
- Phone/meeting transcripts

**Scale by capability, not by user.**

## Scaling Triggers

| Component | Scale Based On | Metric |
|-----------|---------------|--------|
| Input Processors | Input volume | Messages/second across all sources |
| Orchestrators | Processing complexity | Average response latency |
| Memory Services | Data volume | Memory usage per user partition |
| Tool Executors | Tool usage | Concurrent tool executions |

## Interface Design Compatibility

**Current interfaces already support multi-tenant scaling:**

✅ **Stateless:** All interfaces take context as parameters
✅ **Event-driven:** Designed for event bus routing  
✅ **User context:** `AuthContext` carries user permissions
✅ **Rich context:** `ProcessingContext` enables proper isolation

**Minor additions needed:**
```python
# Add user partitioning
class MemoryStore:
    async def store_memory(self, memory: MemoryObject, user_partition: str)

class ProcessingContext:
    user_partition: str  # For resource isolation
```

## Resource Sharing Strategy

- **Shared:** Tool registries, LLM connection pools, model caches
- **Partitioned:** Memory stores, conversation history, user preferences  
- **Isolated:** Authentication contexts, permission scopes

## Benefits

- **Cost Efficient:** Shared infrastructure and LLM pools
- **Better Learning:** Cross-user pattern detection (privacy-preserving)
- **Elastic Scaling:** Scale components independently by actual load
- **Resource Optimization:** No idle per-user instances