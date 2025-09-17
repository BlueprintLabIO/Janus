"""
Input Processing Interfaces

Handles conversion of validated input to JanusEvent objects.

Design Philosophy:
- Aggressive Normalization: All content becomes text + metadata
- Event-Centric: Everything becomes a JanusEvent for the event bus
- Context Preservation: Rich context attached to events for downstream processing
- Metadata Rich: Preserve original format information in structured metadata
- Single Responsibility: Processing only converts format, doesn't make routing decisions

Key Insight: This is where our "aggressive text normalization" strategy is implemented.
All input formats (JSON, Slack messages, webhooks, files) become TextContent with
rich metadata preserving the original format information.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from ...core import JanusEvent, TextContent, EventContext, Result, ProcessingError
from .models import AuthContext, ValidatedInput, ProcessingContext


class ProcessingError(ProcessingError):
    """
    Specific error type for processing failures.
    
    Design Decision: Use specific error types for processing failures
    to distinguish them from validation or authentication failures.
    """
    error_type: str = "processing_error"
    
    # Processing-specific fields
    processing_stage: str = ""  # "normalization", "event_creation", etc.
    content_type: str = ""      # Type of content being processed
    original_format: str = ""   # Original input format


class ContentNormalizer(ABC):
    """
    Normalizes content from various formats to TextContent.
    
    Responsibility: Implement the "aggressive text normalization" strategy.
    Convert any input format to TextContent while preserving original information.
    
    Design Decision: Separate content normalization from event creation
    because normalization logic can be complex and format-specific while
    event creation is consistent across all formats.
    
    This is where the magic happens - PDFs become text + page metadata,
    images become OCR text + image descriptions, Slack messages become
    text + channel/user metadata, etc.
    """
    
    @property
    @abstractmethod
    def supported_content_types(self) -> List[str]:
        """
        Content types this normalizer can handle.
        
        Returns:
            List of content type identifiers
            
        Examples:
            ["text", "slack_message", "discord_message"]
            ["pdf", "image", "document"]
            ["webhook_github", "webhook_stripe"]
        """
        pass
    
    @abstractmethod
    async def normalize_content(
        self, 
        validated_input: ValidatedInput,
        auth_context: AuthContext
    ) -> Result[TextContent, ProcessingError]:
        """
        Convert validated input to normalized TextContent.
        
        Args:
            validated_input: Input that passed validation
            auth_context: Authentication context for processing decisions
            
        Returns:
            Result containing TextContent or processing error
            
        Responsibilities:
            1. Extract text from any format (OCR, parsing, conversion)
            2. Preserve original format information in metadata
            3. Extract and structure format-specific metadata
            4. Handle attachments as references
            5. Set extraction confidence based on conversion quality
            
        Key Principle: NEVER lose information. If something can't be converted
        to text, preserve it in metadata and note the limitation.
        
        Examples:
            PDF Input:
                text = "Chapter 1: Introduction\nThis document explains..."
                original_format = "pdf"
                metadata = {"page_count": 5, "file_size": 1024000, "pdf_version": "1.4"}
                
            Slack Message:
                text = "Hey team, can we review the design doc?"
                original_format = "slack_message"
                metadata = {
                    "channel": "general", 
                    "user": "john_doe", 
                    "timestamp": "1234567890.123456",
                    "message_type": "message"
                }
                
            Image (with OCR):
                text = "Sign says: 'Welcome to our store'"
                original_format = "image"
                metadata = {
                    "image_description": "Photo of a store sign",
                    "ocr_confidence": 0.85,
                    "image_format": "jpeg",
                    "dimensions": "1024x768"
                }
                extraction_confidence = 0.85
        """
        pass
    
    async def extract_text_from_format(
        self, 
        content_data: Any, 
        format_type: str
    ) -> Result[str, ProcessingError]:
        """
        Extract text from specific format (helper method).
        
        Args:
            content_data: Raw content data
            format_type: Format identifier
            
        Returns:
            Result containing extracted text
            
        Design Decision: Separate text extraction from metadata extraction
        for cleaner testing and easier format-specific implementations.
        
        Override this in subclasses for format-specific extraction logic.
        """
        if isinstance(content_data, str):
            return Result.success(content_data)
        elif isinstance(content_data, dict) and "text" in content_data:
            return Result.success(str(content_data["text"]))
        else:
            return Result.error(ProcessingError(
                error_type="text_extraction_error",
                message=f"Cannot extract text from format: {format_type}",
                component=self.__class__.__name__,
                processing_stage="text_extraction",
                content_type=format_type
            ))
    
    async def extract_format_metadata(
        self, 
        content_data: Any, 
        format_type: str
    ) -> Dict[str, Any]:
        """
        Extract format-specific metadata (helper method).
        
        Args:
            content_data: Raw content data
            format_type: Format identifier
            
        Returns:
            Dictionary of format-specific metadata
            
        Override this in subclasses for format-specific metadata extraction.
        """
        return {
            "original_format": format_type,
            "processed_at": datetime.utcnow().isoformat(),
            "normalizer": self.__class__.__name__
        }


class EventBuilder(ABC):
    """
    Builds JanusEvent objects from normalized content.
    
    Responsibility: Create complete JanusEvent with proper context and metadata.
    This is where content + context becomes a complete event for the event bus.
    
    Design Decision: Separate event building from content normalization
    because event creation involves routing decisions and context assembly
    while content normalization is purely about format conversion.
    """
    
    @abstractmethod
    async def build_event(
        self, 
        content: TextContent,
        processing_context: ProcessingContext
    ) -> Result[JanusEvent, ProcessingError]:
        """
        Build complete JanusEvent from normalized content and context.
        
        Args:
            content: Normalized text content
            processing_context: Complete processing context
            
        Returns:
            Result containing JanusEvent or processing error
            
        Responsibilities:
            1. Create EventContext from AuthContext and processing metadata
            2. Determine appropriate event type based on content
            3. Generate event, stream, and trace IDs
            4. Set event relationships (threading, correlation)
            5. Attach processing metadata
            
        Design Decision: Event builder has access to complete processing context
        so it can make intelligent decisions about event type, routing, and
        relationship to other events.
        
        Examples:
            Regular text message: event_type = "input.message.text"
            Command message: event_type = "input.command.text"
            File upload: event_type = "input.file.processed"
        """
        pass
    
    async def create_event_context(
        self, 
        processing_context: ProcessingContext
    ) -> EventContext:
        """
        Create EventContext from ProcessingContext.
        
        Args:
            processing_context: Complete processing context
            
        Returns:
            EventContext for the JanusEvent
            
        Design Decision: Separate method for context creation allows
        easier customization and testing of context assembly logic.
        """
        auth = processing_context.auth_context
        
        return EventContext(
            user_id=auth.user_id,
            session_id=auth.session_id or processing_context.stream_id or auth.user_id,
            source_type=auth.source_type,
            source_id=auth.source_id,
            permissions=auth.granted_permissions,
            priority="normal",  # Could be determined from content analysis
            metadata={
                "processing_pipeline": processing_context.processing_steps,
                "authentication_method": auth.auth_metadata.get("method", "unknown"),
                "processing_time_ms": (
                    datetime.utcnow() - processing_context.pipeline_start_time
                ).total_seconds() * 1000,
                **processing_context.adapter_context
            }
        )
    
    async def determine_event_type(
        self, 
        content: TextContent,
        processing_context: ProcessingContext
    ) -> str:
        """
        Determine appropriate event type based on content and context.
        
        Args:
            content: Normalized content
            processing_context: Processing context
            
        Returns:
            Event type string
            
        Design Decision: Event type determination based on content analysis
        rather than just input source allows more intelligent routing.
        
        Examples:
            "/help" -> "input.command.help"
            "Calculate 2+2" -> "input.message.text" (let orchestrator decide if it's a tool call)
            File upload -> "input.file.processed"
        """
        # Simple heuristics - can be enhanced with ML classification
        text = content.text.strip().lower()
        
        if text.startswith("/") or text.startswith("!"):
            return "input.command.text"
        elif processing_context.validated_input.content_type == "file_upload":
            return "input.file.processed"
        elif "attachments" in content.metadata:
            return "input.message.with_attachments"
        else:
            return "input.message.text"
    
    async def generate_event_ids(
        self, 
        processing_context: ProcessingContext
    ) -> Dict[str, str]:
        """
        Generate event, stream, and trace IDs.
        
        Args:
            processing_context: Processing context
            
        Returns:
            Dictionary with generated IDs
            
        Design Decision: Centralized ID generation allows consistent
        ID strategies and easier correlation across events.
        """
        event_id = str(uuid4())
        
        # Use existing stream_id or create new one
        stream_id = (
            processing_context.stream_id or 
            processing_context.auth_context.session_id or
            f"stream_{event_id[:8]}"
        )
        
        # Trace ID for distributed tracing
        trace_id = str(uuid4())
        
        return {
            "event_id": event_id,
            "stream_id": stream_id,
            "trace_id": trace_id
        }


class InputProcessor(ABC):
    """
    Main processing interface that orchestrates content normalization and event creation.
    
    Responsibility: Coordinate the complete processing pipeline from ValidatedInput to JanusEvent.
    This is the main interface that input pipelines interact with.
    
    Design Decision: Compose ContentNormalizer + EventBuilder rather than
    inheriting. This allows flexible processing strategies while maintaining
    a consistent interface.
    
    This is where validated input becomes a JanusEvent ready for the event bus.
    """
    
    def __init__(
        self,
        content_normalizer: ContentNormalizer,
        event_builder: EventBuilder
    ):
        """
        Initialize with composed normalization and event building strategies.
        
        Args:
            content_normalizer: Handles content format normalization
            event_builder: Handles JanusEvent creation
            
        Design Decision: Dependency injection allows different processing
        strategies for different input types while maintaining the same interface.
        """
        self.content_normalizer = content_normalizer
        self.event_builder = event_builder
    
    @abstractmethod
    async def process(
        self, 
        validated_input: ValidatedInput,
        auth_context: AuthContext
    ) -> Result[JanusEvent, ProcessingError]:
        """
        Process validated input into a JanusEvent.
        
        This orchestrates the complete processing pipeline:
        1. Create ProcessingContext
        2. Normalize content to TextContent
        3. Build JanusEvent with complete context
        
        Args:
            validated_input: Input that passed validation
            auth_context: Authentication context
            
        Returns:
            Result containing JanusEvent or processing error
            
        Design Decision: Return JanusEvent rather than publishing it
        because the caller (pipeline) should control when/how events
        are published to the event bus.
        
        Key Insight: This is where the input processing pipeline ends
        and the event-driven system begins. The JanusEvent is ready
        for the event bus and downstream processing.
        """
        pass
    
    async def create_processing_context(
        self,
        validated_input: ValidatedInput,
        auth_context: AuthContext,
        adapter_context: Optional[Dict[str, Any]] = None
    ) -> ProcessingContext:
        """
        Create ProcessingContext for the processing pipeline.
        
        Args:
            validated_input: Validated input
            auth_context: Authentication context
            adapter_context: Optional adapter-specific context
            
        Returns:
            Complete ProcessingContext
            
        Design Decision: Separate method for context creation allows
        easier testing and customization of context assembly.
        """
        return ProcessingContext(
            auth_context=auth_context,
            validated_input=validated_input,
            pipeline_start_time=datetime.utcnow(),
            processing_steps=["authentication", "validation"],
            adapter_context=adapter_context or {}
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of processing components.
        
        Returns:
            Dictionary of component health status
        """
        return {
            "content_normalizer": True,  # Add real health check
            "event_builder": True        # Add real health check
        }