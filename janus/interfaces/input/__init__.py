"""
Input Interface Definitions for Janus

This module defines the complete input processing pipeline using multiple
small interfaces rather than one monolithic adapter interface.

Design Philosophy:
- Interface Segregation: Each interface has a single responsibility
- Composition over Inheritance: Combine small interfaces into adapters
- Explicit Error Handling: Result pattern at every boundary
- Execution-time Permissions: No permission guessing at input time
- Security by Default: Auth required for every request

Pipeline Order (fixed for security and logical flow):
1. Authentication: Verify credentials and establish permission context
2. Validation: Check format, structure, and basic safety (no permission guessing)
3. Processing: Convert to normalized JanusEvent with full context
"""

from .models import (
    SourceCredentials,
    AuthContext, 
    ValidatedInput,
    ProcessingContext,
    InputCapability
)

from .authentication import (
    InputAuthenticator,
    CredentialValidator,
    PermissionResolver
)

from .validation import (
    InputValidator,
    FormatValidator,
    SafetyValidator
)

from .processing import (
    InputProcessor,
    ContentNormalizer,
    EventBuilder
)

from .capabilities import (
    CapabilityProvider,
    CapabilityRegistry
)

from .pipeline import (
    InputPipeline,
    PipelineResult
)

__all__ = [
    # Data Models
    "SourceCredentials",
    "AuthContext",
    "ValidatedInput", 
    "ProcessingContext",
    "InputCapability",
    
    # Authentication Interfaces
    "InputAuthenticator",
    "CredentialValidator",
    "PermissionResolver",
    
    # Validation Interfaces
    "InputValidator",
    "FormatValidator",
    "SafetyValidator",
    
    # Processing Interfaces
    "InputProcessor",
    "ContentNormalizer",
    "EventBuilder",
    
    # Capability Interfaces
    "CapabilityProvider",
    "CapabilityRegistry",
    
    # Pipeline Orchestration
    "InputPipeline",
    "PipelineResult"
]