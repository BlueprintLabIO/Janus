# Technology Stack

## Overview

Janus uses a modern Python stack optimized for AI workloads, async operations, and microservice architecture. The stack is designed to start simple for MVP and scale to production needs.

## Core Application Stack

### Web Framework: FastAPI + Gunicorn + Uvicorn
**Choice**: FastAPI with Gunicorn (production) or Uvicorn (development)

**Justification**:
- **Async-First**: Native async/await support perfect for LLM API calls and webhook handling
- **Type Safety**: Pydantic integration provides automatic request/response validation
- **Auto Documentation**: Generates OpenAPI specs automatically for all endpoints
- **Performance**: Among the fastest Python web frameworks available
- **Developer Experience**: Excellent IDE support and debugging capabilities

**Alternatives Considered**:
- **Django**: Too heavyweight, synchronous by default, ORM conflicts with our data patterns
- **Flask**: Requires extensive async retrofitting, more manual configuration
- **Quart**: Less mature ecosystem, fewer examples and plugins available

### HTTP Client: httpx
**Choice**: httpx for all external HTTP communication

**Justification**:
- **Async Consistency**: Matches FastAPI's async architecture perfectly
- **Modern API**: requests-like interface with async/await support
- **HTTP/2 Support**: Better performance for multiple LLM API calls
- **Testing Integration**: Excellent testing support with async client
- **Connection Pooling**: Efficient reuse of connections to LLM providers

**Alternatives Considered**:
- **aiohttp**: More complex API, verbose session management
- **requests**: Synchronous, doesn't fit async architecture
- **urllib**: Too low-level, missing conveniences

## Data Storage Layer

### Primary Database: PostgreSQL + pgvector
**Choice**: PostgreSQL with pgvector extension

**Justification**:
- **Vector Support**: pgvector enables vector operations without separate vector database
- **ACID Compliance**: Reliable transactions for critical user data
- **JSON Support**: JSONB columns for flexible schema evolution
- **Self-Hostable**: No vendor lock-in, complete control over data
- **Mature Ecosystem**: Excellent Python async drivers and tooling
- **Scalability**: Proven scaling characteristics for production workloads

**Alternatives Considered**:
- **SQLite**: Great for development but limited concurrent access
- **MongoDB**: No ACID guarantees, less mature vector search
- **MySQL**: Lacks advanced JSON and vector capabilities

### Caching & Working Memory: Redis
**Choice**: Redis for caching and inter-service communication

**Justification**:
- **In-Memory Performance**: Sub-millisecond access for working memory
- **Data Structures**: Native support for lists, sets, sorted sets for complex caching
- **Pub/Sub**: Event-driven communication between components
- **Persistence Options**: Configurable durability vs performance tradeoffs
- **Clustering**: Built-in horizontal scaling capabilities

**Alternatives Considered**:
- **Memcached**: Too simple, no pub/sub or data structures
- **In-Memory Python**: Not shared across processes, lost on restart

### Vector Database: ChromaDB (Production) + pgvector (MVP)
**Choice**: Hybrid approach based on deployment needs

**MVP Strategy: pgvector**
- **Simplicity**: One less service to deploy and manage
- **ACID Guarantees**: Consistent with other data operations
- **Cost Effective**: No additional infrastructure required

**Production Strategy: ChromaDB**
- **Performance**: Optimized specifically for vector operations
- **Features**: Advanced similarity search and filtering capabilities
- **Self-Hostable**: Maintains data sovereignty requirements
- **Scalability**: Better performance characteristics at scale

**Alternatives Considered**:
- **Pinecone**: Vendor lock-in, not self-hostable
- **Weaviate**: Too complex for initial needs, resource intensive
- **Milvus**: Enterprise-grade but overkill for startup phase

## AI & ML Integration

### LLM Providers: OpenAI + Anthropic SDKs
**Choice**: Direct provider SDKs with custom abstraction layer

**Justification**:
- **Latest Features**: Access to newest model capabilities immediately
- **Performance**: Direct API access without middleware overhead
- **Cost Control**: Fine-grained control over model selection and pricing
- **Reliability**: Official SDKs with better error handling and retry logic

**Alternatives Considered**:
- **LangChain**: Too heavyweight, abstractions hide important details
- **LiteLLM**: Good abstraction but adds dependency and potential latency

### Data Validation: Pydantic v2
**Choice**: Pydantic for all data modeling and validation

**Justification**:
- **Type Safety**: Runtime validation with static type hints
- **Performance**: v2 is significantly faster than v1
- **JSON Schema**: Automatic generation for API documentation
- **FastAPI Integration**: Native integration reduces boilerplate
- **Error Messages**: Clear, actionable validation error messages

## Observability & Monitoring Stack

### Logging: structlog
**Choice**: structlog for all application logging

**Justification**:
- **Structured Output**: JSON logs perfect for log aggregation systems
- **Context Management**: Easy to add request IDs and contextual information
- **Performance**: Lazy evaluation of log messages reduces overhead
- **Integration**: Works well with async code and FastAPI middleware
- **Flexibility**: Easy to add custom processors and formatters

**Alternatives Considered**:
- **Standard logging**: Unstructured text harder to parse and analyze
- **loguru**: Good for development but less production-focused

### Metrics: Prometheus + Client Library
**Choice**: Prometheus metrics with prometheus_client library

**Justification**:
- **Industry Standard**: De facto standard for metrics in cloud-native applications
- **Pull Model**: Metrics scraped rather than pushed, better for reliability
- **Rich Query Language**: PromQL enables sophisticated alerting and analysis
- **Self-Hostable**: Complete control over metrics data and retention
- **Ecosystem**: Excellent integration with Grafana for visualization

**Alternatives Considered**:
- **StatsD + Graphite**: Push model less reliable, more complex setup
- **DataDog/New Relic**: Vendor lock-in, costs scale with usage
- **OpenTelemetry Metrics**: Still maturing, Prometheus more stable

### Distributed Tracing: OpenTelemetry
**Choice**: OpenTelemetry for request tracing across components

**Justification**:
- **Industry Standard**: Vendor-neutral standard for observability
- **Auto-Instrumentation**: Automatic tracing for FastAPI, SQLAlchemy, httpx
- **Flexibility**: Can export to Jaeger, Zipkin, or other backends
- **Future-Proof**: Supported by all major observability vendors
- **Rich Context**: Captures detailed request flow across all components

**Alternatives Considered**:
- **Jaeger directly**: Less flexibility, no auto-instrumentation
- **Custom tracing**: Too much development overhead
- **APM tools**: Vendor lock-in and high costs

### Health Monitoring: Custom Health Checks + Prometheus Alerts
**Choice**: FastAPI health endpoints + Prometheus alerting

**Justification**:
- **Comprehensive**: Check all critical dependencies (DB, Redis, LLM APIs)
- **Integration**: Native FastAPI endpoints easy to implement and test
- **Alerting**: Prometheus AlertManager for flexible alert routing
- **Cost Effective**: No additional SaaS monitoring costs

**Monitoring Strategy**:
- **System Metrics**: CPU, memory, disk usage via node_exporter
- **Application Metrics**: Custom business metrics via prometheus_client  
- **Health Checks**: HTTP endpoints for dependency health
- **Log Analysis**: structlog + ELK stack or similar for log aggregation

## Development & Testing Stack

### Package Management: uv
**Choice**: uv for all Python dependency management

**Justification**:
- **Speed**: 10-100x faster than pip for installations
- **Reliability**: Better dependency resolution than pip
- **Simplicity**: Replaces pip, pipenv, poetry with single tool
- **Virtual Environments**: Built-in venv management
- **Future-Proof**: Built by the Astral team (ruff creators)

### Code Quality: ruff + mypy
**Choice**: ruff for linting/formatting, mypy for type checking

**Justification**:
- **Performance**: ruff is 100x faster than traditional tools (flake8, black, isort)
- **Comprehensive**: Single tool replaces multiple formatters and linters
- **Type Safety**: mypy catches bugs at development time
- **Team Consistency**: Automated formatting reduces review friction

### Testing: pytest + async extensions
**Choice**: pytest with asyncio, mock, coverage, and xdist plugins

**Justification**:
- **Async Support**: Native async test support via pytest-asyncio
- **Parallel Execution**: Faster test runs with pytest-xdist
- **Mocking**: Clean mocking of external services with pytest-mock
- **Coverage**: Built-in coverage reporting
- **Fixtures**: Excellent fixture system for complex test scenarios

## Deployment Strategy

### Containerization: Docker + Docker Compose
**Choice**: Docker for containerization, Docker Compose for local development

**Justification**:
- **Consistency**: Identical environments across development and production
- **Isolation**: Each component runs in isolated environment
- **Scalability**: Easy to scale individual components
- **Self-Hosting**: Complete control over deployment infrastructure

### Production Orchestration: Kubernetes (Optional)
**Choice**: Kubernetes for production deployments requiring scale

**Justification**:
- **Scalability**: Automatic scaling based on load
- **Reliability**: Built-in health checks and restart policies
- **Resource Management**: Efficient resource allocation across components
- **Industry Standard**: Well-understood deployment model

**Alternative**: Docker Compose + systemd for simpler deployments

## Configuration Management

### Environment Configuration: Python-decouple + YAML
**Choice**: Environment variables with YAML configuration files

**Justification**:
- **Security**: Secrets via environment variables, not in code
- **Flexibility**: YAML for complex configuration, env vars for secrets
- **12-Factor App**: Follows cloud-native configuration principles
- **Version Control**: Configuration templates in git, secrets separate

## Security Considerations

### Authentication: JWT + OAuth2 (Optional)
**Choice**: JWT tokens with optional OAuth2 integration

**Justification**:
- **Stateless**: No server-side session storage required
- **Standards**: Industry standard token format
- **Integration**: Works well with external identity providers
- **Self-Contained**: Tokens carry all necessary information

### Secrets Management: Environment Variables + Docker Secrets
**Choice**: Environment variables for development, Docker secrets for production

**Justification**:
- **Simplicity**: No additional secret management infrastructure required
- **Security**: Secrets not stored in container images or code
- **Flexibility**: Easy to integrate with external secret managers later

This technology stack provides a solid foundation for building Janus while maintaining the flexibility to evolve components as requirements change. The choices prioritize developer productivity, operational simplicity, and long-term maintainability while avoiding vendor lock-in where possible.