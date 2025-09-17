"""
Input Validation Interfaces

Handles format and safety validation of input after authentication.

Design Philosophy:
- No Permission Guessing: Validation only checks format/safety, not permissions
- Fail Fast: Invalid input stops processing immediately
- Safety First: Protect against malicious input (size limits, content scanning)
- Format Agnostic: Handle any input format through pluggable validators
- Preserve Context: Keep original input for debugging while creating normalized version

Key Insight: We deliberately do NOT check permissions here because we can't
accurately predict what permissions will be needed until execution time.
This keeps validation simple and execution-time permission checking accurate.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import time

from ...core import Result, ProcessingError
from .models import AuthContext, ValidatedInput


class ValidationError(ProcessingError):
    """
    Specific error type for validation failures.
    
    Design Decision: Use specific error types for different validation failures.
    This allows callers to handle validation errors appropriately.
    """
    error_type: str = "validation_error"
    
    # Validation-specific fields
    validation_stage: str = ""  # "format", "safety", "size", etc.
    field_errors: Dict[str, str] = {}  # Field-specific error messages
    suggested_fix: Optional[str] = None  # How to fix the validation error


class FormatValidator(ABC):
    """
    Validates input format and structure.
    
    Responsibility: Ensure input has expected structure and can be processed.
    This is about data integrity, not business logic or permissions.
    
    Design Decision: Separate format validation from safety validation
    because they have different concerns and may have different implementations.
    
    Examples:
    - JSON input: Valid JSON structure, required fields present
    - Slack message: Expected payload structure, valid timestamp
    - Webhook: Required headers present, payload structure valid
    """
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """
        Input formats this validator can handle.
        
        Returns:
            List of format identifiers this validator supports
            
        Examples:
            ["json", "form_data"]
            ["slack_message", "slack_event"]
            ["webhook_github", "webhook_stripe"]
        """
        pass
    
    @abstractmethod
    async def validate_format(
        self, 
        raw_input: Any,
        auth_context: AuthContext
    ) -> Result[Dict[str, Any], ValidationError]:
        """
        Validate input format and return normalized structure.
        
        Args:
            raw_input: Raw input from the source
            auth_context: Authentication context (for context, not permission checking)
            
        Returns:
            Result containing normalized input dict or validation error
            
        Responsibilities:
            1. Check input has expected structure
            2. Validate required fields are present
            3. Normalize to standard format
            4. Extract metadata for processing
            
        Should NOT:
            - Check permissions (that happens at execution time)
            - Make business logic decisions
            - Perform expensive operations
            
        Design Decision: Return normalized dict rather than typed object
        because different input sources have different structures and we
        want to avoid complex type hierarchies.
        
        Examples:
            Input: {"text": "hello", "channel": "general", "user": "john"}
            Output: {"text": "hello", "metadata": {"channel": "general", "user": "john"}}
        """
        pass
    
    async def extract_content_metadata(
        self, 
        normalized_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract content metadata from normalized input.
        
        Args:
            normalized_input: Input that passed format validation
            
        Returns:
            Dictionary of content metadata
            
        Purpose: Extract information about the content itself rather than
        the delivery mechanism. This helps with content processing decisions.
        
        Examples:
            {"content_type": "text", "language": "en", "has_attachments": false}
            {"content_type": "command", "command_name": "help", "parameters": []}
        """
        return {
            "detected_content_type": "text",
            "format_version": "1.0",
            "normalized_at": datetime.utcnow().isoformat()
        }


class SafetyValidator(ABC):
    """
    Validates input safety and applies security controls.
    
    Responsibility: Protect the system from malicious or problematic input.
    This is about security and system protection, not business logic.
    
    Design Decision: Separate safety from format validation because safety
    may require different techniques (scanning, size limits, etc.) and
    may be configurable based on deployment security requirements.
    
    Examples:
    - Size limits: Reject overly large inputs
    - Content scanning: Check for malicious patterns
    - Rate limiting: Prevent spam/abuse (though this might be elsewhere)
    """
    
    @property
    @abstractmethod
    def safety_checks(self) -> List[str]:
        """
        List of safety checks this validator performs.
        
        Returns:
            List of safety check identifiers
            
        Examples:
            ["size_limit", "malware_scan", "content_filter"]
            ["injection_scan", "rate_limit", "spam_detection"]
        """
        pass
    
    @abstractmethod
    async def validate_safety(
        self, 
        normalized_input: Dict[str, Any],
        auth_context: AuthContext
    ) -> Result[Dict[str, Any], ValidationError]:
        """
        Validate input safety and return safety metadata.
        
        Args:
            normalized_input: Input that passed format validation
            auth_context: Authentication context for safety decisions
            
        Returns:
            Result containing safety metadata or validation error
            
        Responsibilities:
            1. Check input size is within limits
            2. Scan for malicious content patterns
            3. Apply security policies based on user/source
            4. Return safety assessment metadata
            
        Should NOT:
            - Check business logic or permissions
            - Modify the input content
            - Make routing decisions
            
        Design Decision: Return safety metadata rather than just pass/fail
        because some processors may want to handle "questionable" input
        differently (e.g., with extra logging or user confirmation).
        
        Examples:
            Output: {
                "safety_score": 0.95,
                "checks_passed": ["size_limit", "malware_scan"],
                "warnings": ["unusual_encoding"],
                "size_bytes": 1024
            }
        """
        pass
    
    async def get_size_limits(self, auth_context: AuthContext) -> Dict[str, int]:
        """
        Get size limits for the authenticated user/source.
        
        Args:
            auth_context: Authentication context
            
        Returns:
            Dictionary of size limits
            
        Design Decision: Make size limits configurable based on user/source
        because different users may have different limits (free vs paid,
        internal vs external, etc.).
        
        Examples:
            {"max_text_length": 10000, "max_total_size": 1048576}
        """
        return {
            "max_text_length": 10000,      # 10KB of text
            "max_total_size": 1048576,     # 1MB total
            "max_attachments": 5
        }


class InputValidator(ABC):
    """
    Main validation interface that orchestrates format and safety validation.
    
    Responsibility: Coordinate the complete validation process and produce ValidatedInput.
    This is the main interface that input pipelines interact with.
    
    Design Decision: Compose FormatValidator + SafetyValidator rather than
    inheriting. This allows flexible validation strategies while maintaining
    a consistent interface.
    
    Key Principle: Validation is about making sure we CAN process the input safely,
    not about whether the user is ALLOWED to perform the requested action.
    Permission checking happens later during execution.
    """
    
    def __init__(
        self,
        format_validator: FormatValidator,
        safety_validator: SafetyValidator
    ):
        """
        Initialize with composed format and safety validation strategies.
        
        Args:
            format_validator: Handles input format validation
            safety_validator: Handles input safety validation
            
        Design Decision: Dependency injection allows different validation
        strategies for different input types while maintaining the same interface.
        """
        self.format_validator = format_validator
        self.safety_validator = safety_validator
    
    @abstractmethod
    async def validate(
        self, 
        raw_input: Any,
        auth_context: AuthContext
    ) -> Result[ValidatedInput, ValidationError]:
        """
        Perform complete validation and return ValidatedInput.
        
        This orchestrates the complete validation process:
        1. Format validation and normalization
        2. Safety validation and security checks
        3. ValidatedInput creation with metadata
        
        Args:
            raw_input: Raw input from the source
            auth_context: Authentication context
            
        Returns:
            Result containing ValidatedInput or validation error
            
        Design Decision: Return ValidatedInput object rather than just the
        normalized data because processors need the validation metadata
        for processing decisions.
        
        Key Insight: We pass auth_context to validators but only for context
        (user type, source type) not for permission checking. Permissions
        are checked later during execution when we know what's needed.
        """
        pass
    
    async def create_validated_input(
        self,
        raw_input: Any,
        normalized_input: Dict[str, Any],
        safety_metadata: Dict[str, Any],
        validation_start_time: float
    ) -> ValidatedInput:
        """
        Create ValidatedInput from validation results.
        
        Args:
            raw_input: Original raw input
            normalized_input: Normalized input data
            safety_metadata: Safety validation results
            validation_start_time: When validation started (for timing)
            
        Returns:
            Complete ValidatedInput object
            
        Design Decision: Separate method for ValidatedInput creation allows
        easier testing and customization of validation result packaging.
        """
        processing_time_ms = int((time.time() - validation_start_time) * 1000)
        
        # Detect content type from normalized input
        content_type = self._detect_content_type(normalized_input)
        
        # Calculate input size
        input_size = self._calculate_input_size(raw_input)
        
        # Extract any validation warnings
        warnings = safety_metadata.get("warnings", [])
        
        return ValidatedInput(
            raw_input=raw_input,
            normalized_input=normalized_input,
            validation_confidence=safety_metadata.get("safety_score", 1.0),
            validation_warnings=warnings,
            detected_language=self._detect_language(normalized_input),
            content_type=content_type,
            input_size_bytes=input_size,
            processing_time_ms=processing_time_ms
        )
    
    def _detect_content_type(self, normalized_input: Dict[str, Any]) -> str:
        """
        Detect content type from normalized input.
        
        Args:
            normalized_input: Normalized input data
            
        Returns:
            Content type string
            
        Simple heuristics for content type detection.
        More sophisticated detection can be added later.
        """
        if "text" in normalized_input:
            text = normalized_input["text"]
            if text.startswith("/") or text.startswith("!"):
                return "command"
            elif "attachments" in normalized_input:
                return "text_with_attachments"
            else:
                return "text"
        elif "file" in normalized_input:
            return "file_upload"
        else:
            return "unknown"
    
    def _detect_language(self, normalized_input: Dict[str, Any]) -> Optional[str]:
        """
        Detect language from text content.
        
        Args:
            normalized_input: Normalized input data
            
        Returns:
            Language code or None
            
        Simple language detection - can be enhanced with proper language
        detection libraries later.
        """
        text = normalized_input.get("text", "")
        if not text:
            return None
        
        # Very simple heuristics - replace with proper language detection
        if any(word in text.lower() for word in ["the", "and", "or", "but"]):
            return "en"
        elif any(word in text.lower() for word in ["el", "la", "y", "o"]):
            return "es"
        else:
            return "en"  # Default to English
    
    def _calculate_input_size(self, raw_input: Any) -> int:
        """
        Calculate size of raw input in bytes.
        
        Args:
            raw_input: Raw input data
            
        Returns:
            Size in bytes
        """
        if isinstance(raw_input, str):
            return len(raw_input.encode('utf-8'))
        elif isinstance(raw_input, bytes):
            return len(raw_input)
        elif isinstance(raw_input, dict):
            # Rough estimate for dict size
            import json
            return len(json.dumps(raw_input, default=str).encode('utf-8'))
        else:
            # Fallback estimate
            return len(str(raw_input).encode('utf-8'))
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of validation components.
        
        Returns:
            Dictionary of component health status
        """
        return {
            "format_validator": True,  # Add real health check
            "safety_validator": True   # Add real health check
        }