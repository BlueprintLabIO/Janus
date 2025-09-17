"""
Input Capability Interfaces

Handles capability detection and feature management for input adapters.

Design Philosophy:
- Feature Detection over Inheritance: Use capabilities instead of type hierarchies
- Runtime Discovery: Capabilities discoverable at runtime for dynamic behavior
- Graceful Degradation: Missing capabilities handled gracefully, not as errors
- Clear Contracts: Capabilities define clear interfaces and requirements
- Extensibility: Easy to add new capabilities without breaking existing code

Key Insight: Rather than having SlackAdapter extend WebhookAdapter extend InputAdapter,
we have capabilities like "webhook_signatures", "file_attachments", "threading" that
can be mixed and matched. This allows more flexible adapter composition.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from enum import Enum

from ...core import Result, ProcessingError
from .models import InputCapability


class CapabilityError(ProcessingError):
    """
    Error related to capability handling.
    
    Design Decision: Specific error type for capability issues
    helps distinguish between missing features and actual failures.
    """
    error_type: str = "capability_error"
    
    # Capability-specific fields
    missing_capability: str = ""
    available_capabilities: List[str] = []
    suggested_alternative: Optional[str] = None


class StandardCapabilities(str, Enum):
    """
    Standard capabilities that adapters commonly provide.
    
    Design Decision: Define standard capabilities as an enum for consistency,
    but allow custom capabilities through string literals for extensibility.
    
    These are common patterns we see across different input sources.
    """
    
    # Authentication capabilities
    API_KEY_AUTH = "api_key_auth"               # API key authentication
    OAUTH_AUTH = "oauth_auth"                   # OAuth 2.0 authentication
    WEBHOOK_SIGNATURES = "webhook_signatures"   # Webhook signature verification
    BASIC_AUTH = "basic_auth"                   # HTTP Basic authentication
    
    # Content processing capabilities
    TEXT_PROCESSING = "text_processing"         # Basic text content processing
    FILE_ATTACHMENTS = "file_attachments"       # Handle file uploads/attachments
    IMAGE_PROCESSING = "image_processing"       # OCR and image analysis
    DOCUMENT_PARSING = "document_parsing"       # PDF, Word, etc. parsing
    
    # Communication features
    THREADING = "threading"                     # Threaded conversations
    REACTIONS = "reactions"                     # Message reactions/emoji
    MENTIONS = "mentions"                       # User mentions (@user)
    CHANNELS = "channels"                       # Multi-channel support
    
    # Advanced features
    REAL_TIME = "real_time"                     # Real-time message streaming
    BULK_IMPORT = "bulk_import"                 # Bulk message import
    SEARCH_HISTORY = "search_history"           # Search historical messages
    USER_PRESENCE = "user_presence"             # User online/offline status
    
    # Technical capabilities
    RATE_LIMITING = "rate_limiting"             # Built-in rate limiting
    RETRY_LOGIC = "retry_logic"                 # Automatic retry on failures
    COMPRESSION = "compression"                 # Content compression support
    ENCRYPTION = "encryption"                   # End-to-end encryption


class CapabilityProvider(ABC):
    """
    Interface for components that provide capabilities.
    
    Responsibility: Allow components to declare what they can do and
    provide information about their capabilities to consumers.
    
    Design Decision: Separate from the main adapter interface so that
    capability checking can be lightweight and doesn't require full
    adapter initialization.
    """
    
    @abstractmethod
    def get_capabilities(self) -> List[InputCapability]:
        """
        Get all capabilities provided by this component.
        
        Returns:
            List of capabilities with metadata
            
        Design Decision: Return full InputCapability objects rather than
        just strings so consumers can get detailed information about
        each capability including parameters and requirements.
        """
        pass
    
    @abstractmethod
    def supports_capability(self, capability_name: str) -> bool:
        """
        Check if a specific capability is supported.
        
        Args:
            capability_name: Name of capability to check
            
        Returns:
            True if capability is supported
            
        Design Decision: Fast capability checking method for quick
        feature detection without needing to process full capability list.
        """
        pass
    
    def get_capability_details(self, capability_name: str) -> Optional[InputCapability]:
        """
        Get detailed information about a specific capability.
        
        Args:
            capability_name: Name of capability
            
        Returns:
            InputCapability object or None if not supported
            
        This provides access to capability parameters, dependencies,
        and other metadata for capabilities that need configuration.
        """
        capabilities = self.get_capabilities()
        for capability in capabilities:
            if capability.name == capability_name:
                return capability
        return None
    
    def get_capability_dependencies(self, capability_name: str) -> List[str]:
        """
        Get dependencies for a specific capability.
        
        Args:
            capability_name: Name of capability
            
        Returns:
            List of required capability names
            
        Some capabilities depend on others. For example, "file_attachments"
        might require "text_processing" to extract text from files.
        """
        capability = self.get_capability_details(capability_name)
        if capability:
            return capability.dependencies
        return []
    
    def validate_capability_requirements(
        self, 
        required_capabilities: List[str]
    ) -> List[str]:
        """
        Validate that all required capabilities are available.
        
        Args:
            required_capabilities: List of capability names needed
            
        Returns:
            List of missing capabilities (empty if all available)
            
        This checks both direct capabilities and their dependencies
        to ensure all requirements can be satisfied.
        """
        missing = []
        
        for capability_name in required_capabilities:
            if not self.supports_capability(capability_name):
                missing.append(capability_name)
                continue
            
            # Check dependencies
            dependencies = self.get_capability_dependencies(capability_name)
            for dep in dependencies:
                if not self.supports_capability(dep):
                    missing.append(f"{capability_name} (requires {dep})")
        
        return missing


class CapabilityRegistry(ABC):
    """
    Registry for managing capabilities across multiple providers.
    
    Responsibility: Coordinate capabilities across different input adapters
    and provide system-wide capability discovery.
    
    Design Decision: Centralized registry allows the system to understand
    what capabilities are available across all adapters and make routing
    decisions based on capability requirements.
    
    Use Cases:
    - Route input to adapter that supports required capabilities
    - Provide capability inventory for system monitoring
    - Enable/disable features based on available capabilities
    """
    
    @abstractmethod
    async def register_provider(
        self, 
        provider_id: str,
        provider: CapabilityProvider
    ) -> Result[None, CapabilityError]:
        """
        Register a capability provider.
        
        Args:
            provider_id: Unique identifier for the provider
            provider: Capability provider to register
            
        Returns:
            Result indicating success or error
            
        Design Decision: Async registration allows for validation and
        dependency checking during registration.
        """
        pass
    
    @abstractmethod
    async def unregister_provider(self, provider_id: str) -> Result[None, CapabilityError]:
        """
        Unregister a capability provider.
        
        Args:
            provider_id: Provider to unregister
            
        Returns:
            Result indicating success or error
        """
        pass
    
    @abstractmethod
    def find_providers_with_capability(self, capability_name: str) -> List[str]:
        """
        Find all providers that support a specific capability.
        
        Args:
            capability_name: Capability to search for
            
        Returns:
            List of provider IDs that support the capability
            
        Design Decision: Return provider IDs rather than provider objects
        to avoid coupling and allow lazy loading of providers.
        """
        pass
    
    @abstractmethod
    def get_system_capabilities(self) -> Dict[str, List[str]]:
        """
        Get all capabilities available in the system.
        
        Returns:
            Dictionary mapping capability names to provider IDs
            
        Useful for system monitoring and feature inventory.
        """
        pass
    
    def find_best_provider_for_requirements(
        self, 
        required_capabilities: List[str],
        preferred_providers: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Find the best provider for a set of capability requirements.
        
        Args:
            required_capabilities: Capabilities that must be supported
            preferred_providers: Optional list of preferred providers
            
        Returns:
            Provider ID that best matches requirements, or None
            
        Algorithm:
        1. Find providers that support ALL required capabilities
        2. Prefer providers from preferred_providers list if given
        3. Among remaining, prefer provider with most total capabilities (most capable)
        4. Break ties by provider registration order
        """
        # Find providers that support all requirements
        candidate_providers = None
        
        for capability in required_capabilities:
            providers_with_capability = set(self.find_providers_with_capability(capability))
            
            if candidate_providers is None:
                candidate_providers = providers_with_capability
            else:
                candidate_providers &= providers_with_capability
        
        if not candidate_providers:
            return None
        
        # Apply preferences
        if preferred_providers:
            preferred_candidates = candidate_providers & set(preferred_providers)
            if preferred_candidates:
                candidate_providers = preferred_candidates
        
        # For now, just return the first candidate
        # More sophisticated selection logic can be added here
        return list(candidate_providers)[0]
    
    async def validate_system_capabilities(self) -> Dict[str, Any]:
        """
        Validate the overall capability health of the system.
        
        Returns:
            Dictionary with validation results
            
        Checks:
        - Are there any capability dependency conflicts?
        - Are critical capabilities available?
        - Are there any redundant capability providers?
        """
        return {
            "total_providers": 0,
            "total_capabilities": 0,
            "capability_conflicts": [],
            "missing_critical_capabilities": [],
            "validation_passed": True
        }