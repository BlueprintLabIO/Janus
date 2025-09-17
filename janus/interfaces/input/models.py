"""
Input Interface Data Models

Core data structures used throughout the input processing pipeline.
These models define the contracts between different processing stages.

Design Decisions:
- Immutable data structures where possible for thread safety
- Rich type annotations for IDE support and runtime validation
- Pydantic for automatic serialization and validation
- Explicit separation between credentials, auth context, and processing context
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum


class PermissionScope(str, Enum):
    """
    Hierarchical permission scopes.
    
    Design Decision: Use hierarchical permissions for granular control.
    Examples: "chat", "tools.calculator", "memory.read", "admin.health"
    
    Justification: Allows both broad permissions ("tools.*") and specific 
    permissions ("tools.calculator") with clear inheritance patterns.
    """
    
    # Core functionality
    CHAT = "chat"                           # Basic chat functionality
    
    # Tool permissions (hierarchical)
    TOOLS_ALL = "tools.*"                   # All tools
    TOOLS_CALCULATOR = "tools.calculator"   # Calculator tool
    TOOLS_TIME = "tools.time"               # Time tool
    TOOLS_ECHO = "tools.echo"               # Echo tool
    
    # Memory permissions (read/write separation)
    MEMORY_READ = "memory.read"             # Read memories
    MEMORY_WRITE = "memory.write"           # Store new memories
    MEMORY_DELETE = "memory.delete"         # Delete memories
    
    # Administrative permissions
    ADMIN_HEALTH = "admin.health"           # Health check access
    ADMIN_METRICS = "admin.metrics"         # Metrics access
    ADMIN_CONFIG = "admin.config"           # Configuration changes


class SourceCredentials(BaseModel):
    """
    Credentials provided by an input source.
    
    Design Decision: Keep credentials generic and extensible.
    Different input sources (API, Slack, webhooks) have different credential types.
    
    Security Note: The 'credentials' dict should contain encrypted/hashed values
    when stored, but may contain plaintext during processing.
    """
    
    source_type: str = Field(
        ..., 
        description="Type of input source (api, slack, webhook, discord, etc.)",
        examples=["api", "slack", "webhook", "discord"]
    )
    
    source_id: str = Field(
        ...,
        description="Unique identifier for this specific source instance",
        examples=["slack_workspace_123", "webhook_endpoint_456", "api_key_789"]
    )
    
    credentials: Dict[str, Any] = Field(
        ...,
        description="Source-specific credential data (API keys, tokens, secrets)",
        examples=[
            {"api_key": "sk-1234...", "user_id": "user_123"},
            {"bot_token": "xoxb-1234...", "signing_secret": "abc123"},
            {"webhook_secret": "whsec_1234...", "signature_header": "x-signature"}
        ]
    )
    
    # Permissions granted BY this credential source
    # Note: Final permissions = credential_permissions ∩ user_permissions
    credential_permissions: List[str] = Field(
        default_factory=list,
        description="Permissions granted by this credential (before user intersection)",
        examples=[["chat", "tools.*"], ["chat", "tools.calculator", "memory.read"]]
    )
    
    expires_at: Optional[datetime] = Field(
        None,
        description="When these credentials expire (None = never expires)"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional source-specific metadata",
        examples=[
            {"channel_id": "C1234567890", "team_domain": "myteam"},
            {"webhook_url": "https://api.service.com/webhook", "version": "v1"}
        ]
    )


class AuthContext(BaseModel):
    """
    Authentication context established after credential verification.
    
    Design Decision: Separate auth context from credentials for security.
    This contains the RESULT of authentication, not the raw credentials.
    
    Key Principle: This represents what the user is ALLOWED to do,
    not what they WANT to do (which is determined at execution time).
    """
    
    user_id: str = Field(
        ...,
        description="Authenticated user identifier",
        examples=["user_12345", "slack_user_U1234567890", "api_user_abc"]
    )
    
    source_type: str = Field(
        ...,
        description="Type of source that provided authentication"
    )
    
    source_id: str = Field(
        ..., 
        description="Specific source instance identifier"
    )
    
    # FINAL computed permissions (credential_permissions ∩ user_permissions)
    granted_permissions: List[str] = Field(
        ...,
        description="Final permissions granted to this authenticated context",
        examples=[["chat", "tools.calculator"], ["chat", "memory.read", "memory.write"]]
    )
    
    session_id: Optional[str] = Field(
        None,
        description="Session identifier for this auth context (if applicable)"
    )
    
    authenticated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When authentication was performed"
    )
    
    expires_at: Optional[datetime] = Field(
        None,
        description="When this auth context expires"
    )
    
    # Security metadata
    auth_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the authentication process",
        examples=[
            {"method": "api_key", "ip_address": "192.168.1.100"},
            {"method": "slack_oauth", "workspace_id": "T1234567890"},
            {"method": "webhook_signature", "signature_valid": True}
        ]
    )


class ValidatedInput(BaseModel):
    """
    Input that has passed validation checks.
    
    Design Decision: Keep validation focused on format/safety, not permissions.
    Permission checking happens at execution time when we know what we're actually doing.
    
    This represents input that is:
    1. Structurally valid (proper JSON, expected fields, etc.)
    2. Safe (reasonable size, no malicious content)
    3. Ready for processing
    
    NOT validated for permissions - that happens during execution.
    """
    
    # Original input preserved for debugging/auditing
    raw_input: Any = Field(
        ...,
        description="Original raw input (preserved for debugging)"
    )
    
    # Normalized/cleaned input ready for processing
    normalized_input: Dict[str, Any] = Field(
        ...,
        description="Input normalized to standard format",
        examples=[
            {"text": "Hello world", "metadata": {"channel": "general"}},
            {"text": "Calculate 2+2", "metadata": {"format": "slack_message"}}
        ]
    )
    
    # Validation metadata
    validation_confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in validation (1.0 = perfectly valid)"
    )
    
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal validation warnings",
        examples=[["Large message size", "Unusual characters detected"]]
    )
    
    detected_language: Optional[str] = Field(
        None,
        description="Detected language code (if text input)",
        examples=["en", "es", "fr"]
    )
    
    content_type: str = Field(
        ...,
        description="Type of content detected",
        examples=["text", "text_with_attachments", "command", "file_upload"]
    )
    
    # Size and safety metrics
    input_size_bytes: int = Field(
        ...,
        description="Size of input in bytes"
    )
    
    processing_time_ms: int = Field(
        ...,
        description="Time taken for validation in milliseconds"
    )


class ProcessingContext(BaseModel):
    """
    Complete context for input processing.
    
    Design Decision: Combine auth context with processing metadata.
    This gives processors everything they need to make decisions and create events.
    
    Key Insight: This flows through the entire processing pipeline,
    accumulating information at each stage.
    """
    
    # Authentication context (who and what permissions)
    auth_context: AuthContext = Field(
        ...,
        description="Authentication and permission context"
    )
    
    # Validated input (what they said)
    validated_input: ValidatedInput = Field(
        ...,
        description="Input that passed validation"
    )
    
    # Processing pipeline metadata
    pipeline_start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="When processing started"
    )
    
    processing_steps: List[str] = Field(
        default_factory=list,
        description="Steps completed in processing pipeline",
        examples=[["authentication", "validation", "normalization"]]
    )
    
    # Event generation context
    target_event_type: str = Field(
        "input.message.text",
        description="Type of event to generate"
    )
    
    stream_id: Optional[str] = Field(
        None,
        description="Stream/conversation identifier for event grouping"
    )
    
    thread_id: Optional[str] = Field(
        None,
        description="Thread identifier within conversation"
    )
    
    # Extension points for adapters
    adapter_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific context data",
        examples=[
            {"slack_channel": "C1234567890", "slack_ts": "1234567890.123456"},
            {"webhook_headers": {"x-signature": "sha256=..."}, "webhook_body": "..."}
        ]
    )


class InputCapability(BaseModel):
    """
    A capability that an input processor provides.
    
    Design Decision: Use capabilities for feature detection instead of inheritance.
    This allows adapters to declare what they support without complex type hierarchies.
    
    Benefits:
    - Runtime capability checking
    - Graceful degradation
    - Clear feature boundaries
    - Easy extensibility
    """
    
    name: str = Field(
        ...,
        description="Unique capability identifier",
        examples=["webhook_signatures", "file_attachments", "threading", "reactions"]
    )
    
    description: str = Field(
        ...,
        description="Human-readable capability description",
        examples=[
            "Verify webhook signatures for security",
            "Process file attachments",
            "Handle threaded conversations"
        ]
    )
    
    version: str = Field(
        "1.0",
        description="Capability version for compatibility"
    )
    
    # Capability configuration/parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Capability-specific parameters",
        examples=[
            {"max_file_size": 10485760, "supported_types": ["image/*", "text/*"]},
            {"signature_algorithms": ["sha256", "sha1"], "header_name": "x-signature"}
        ]
    )
    
    # Feature flags
    required: bool = Field(
        False,
        description="Whether this capability is required for the adapter to function"
    )
    
    experimental: bool = Field(
        False,
        description="Whether this capability is experimental/unstable"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other capabilities this one depends on",
        examples=[["file_attachments"], ["webhook_signatures", "json_parsing"]]
    )