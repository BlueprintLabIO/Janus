# Input Processing Architecture

## Overview

Janus processes inputs through a two-stage pipeline: **Adapters** handle source-specific authentication/parsing, **Ingest Module** normalizes events into a unified schema. The input system establishes the foundation for paired output responses.

```
Raw Input → Adapter → Ingest Module → Normalized Event → Orchestrator
```

## Design Principles

### Separation of Concerns
- **Adapters**: Source-specific authentication, parsing, and validation
- **Ingest Module**: Business logic, normalization, and permission resolution
- **Clear Boundaries**: Each layer has distinct responsibilities

### Source-Agnostic Core
- **Unified Schema**: All inputs normalized to common format regardless of origin
- **Consistent Interface**: Orchestrator receives identical event structure from all sources
- **Extensible**: New input sources added without changing downstream logic

### Security by Design
- **Dual-Layer Permissions**: Input source trust level ∩ AI teammate capabilities
- **Authentication Flexibility**: Native platform auth (webhooks, API keys, OAuth2)
- **Principle of Least Privilege**: Each source gets minimum necessary access

### Context Preservation
- **Rich Metadata**: Preserve source-specific context for intelligent responses
- **Conversation Threading**: Maintain discussion continuity across platforms
- **Intent Classification**: Automatic categorization of user intentions

## Architecture Layers

### 1. Adapter Layer (Source-Specific)
- **Slack**: Webhook signature validation, thread context preservation
- **API**: Bearer token authentication, structured request handling  
- **GitHub**: Webhook signature validation, repository context extraction
- **Email**: OAuth2 verification, content parsing and attachment handling

### 2. Ingest Module (Normalization)
- **Event Normalizer**: Convert diverse inputs to unified schema
- **Permission Resolver**: Calculate effective permissions using intersection logic
- **Content Processor**: Extract entities, classify intent, handle multimedia
- **Event Validator**: Ensure schema compliance and data integrity

### 3. Context Enrichment
- **User Identity**: Map platform users to consistent identity system
- **Trust Levels**: Classify input sources by security and reliability
- **Execution Hints**: Derive routing preferences from source characteristics

## Normalized Schema

```json
{
  "event_id": "evt_uuid",
  "timestamp": "2025-01-15T10:30:00Z",
  "source": {
    "type": "slack|api|github|email",
    "identity": { "user_id", "trust_level", "authenticated" },
    "channel": { "id", "name", "type", "is_public" }
  },
  "intent": {
    "action_type": "query|command|notification|alert",
    "urgency": "low|normal|high|critical",
    "expected_response": "text|action|silent"
  },
  "content": {
    "primary": { "type": "text", "data": "message content" },
    "attachments": [{ "type", "reference", "metadata" }]
  },
  "execution_context": {
    "effective_permissions": "resolved permissions",
    "cost_constraints": { "max_cost", "timeout_ms" },
    "routing_hints": { "preferred_models", "execution_strategy" }
  }
}
```

## Benefits

- **Separation of Concerns**: Adapters handle source specifics, Ingest handles business logic
- **Consistent Interface**: Orchestrator receives uniform events regardless of source
- **Extensibility**: Add new sources without changing core logic
- **Security**: Dual-layer permissions (source ∩ teammate capabilities)
- **Observability**: Centralized event processing and validation