"""
Input Pipeline Interface

Orchestrates the complete input processing pipeline from raw input to JanusEvent.

Design Philosophy:
- Pipeline Orchestration: Coordinate all input processing stages
- Fixed Pipeline Order: Auth → Validate → Process (for security and logic)
- Fail Fast: Stop processing at first failure for efficiency and security
- Rich Error Context: Provide detailed error information for debugging
- Auditability: Track complete processing pipeline for compliance/debugging
- Composability: Allow different implementations of each stage

Key Insight: This is the main entry point for input processing. It coordinates
the three main interfaces (authentication, validation, processing) into a
single, easy-to-use pipeline that produces JanusEvents.

Security Note: The fixed pipeline order is critical for security:
1. Authentication MUST happen first (don't process unauthenticated input)
2. Validation MUST happen before processing (don't process invalid input)
3. Processing happens last with full context available
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from ...core import JanusEvent, Result, ProcessingError
from .models import SourceCredentials, ProcessingContext
from .authentication import InputAuthenticator
from .validation import InputValidator
from .processing import InputProcessor


class PipelineError(ProcessingError):
    """
    Error that occurred during pipeline execution.
    
    Design Decision: Pipeline-specific error type that can contain
    information about which stage failed and the complete context.
    """
    error_type: str = "pipeline_error"
    
    # Pipeline-specific fields
    failed_stage: str = ""                          # "authentication", "validation", "processing"
    pipeline_context: Dict[str, Any] = {}           # Context at time of failure
    stage_errors: List[ProcessingError] = []        # Errors from individual stages


class PipelineResult(BaseModel):
    """
    Complete result from pipeline execution.
    
    Design Decision: Rich result object that includes not just the final
    JanusEvent but also metadata about the processing pipeline for
    debugging, monitoring, and compliance.
    """
    
    # Main result
    event: Optional[JanusEvent] = None
    success: bool = False
    error: Optional[PipelineError] = None
    
    # Pipeline execution metadata
    total_processing_time_ms: int = 0
    stage_timings: Dict[str, int] = {}              # Time spent in each stage
    stages_completed: List[str] = []                # Stages that completed successfully
    
    # Context preservation
    processing_context: Optional[ProcessingContext] = None
    
    # Audit trail
    pipeline_id: str = ""                           # Unique identifier for this pipeline run
    started_at: datetime = datetime.utcnow()
    completed_at: Optional[datetime] = None
    
    def mark_completed(self) -> None:
        """Mark pipeline as completed and calculate final timing."""
        self.completed_at = datetime.utcnow()
        if self.completed_at:
            self.total_processing_time_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )


class InputPipeline(ABC):
    """
    Main input processing pipeline interface.
    
    Responsibility: Orchestrate the complete input processing flow from
    raw input to JanusEvent ready for the event bus.
    
    Design Decision: Compose the three main processing interfaces rather
    than inheriting from them. This allows flexible pipeline implementations
    while maintaining consistent behavior.
    
    This is the main interface that external systems (web APIs, webhook handlers,
    etc.) will interact with. It provides a simple process() method that
    handles all the complexity internally.
    """
    
    def __init__(
        self,
        authenticator: InputAuthenticator,
        validator: InputValidator,
        processor: InputProcessor,
        pipeline_id: Optional[str] = None
    ):
        """
        Initialize pipeline with composed processing stages.
        
        Args:
            authenticator: Handles authentication and permission resolution
            validator: Handles input validation and safety checking
            processor: Handles content normalization and event creation
            pipeline_id: Optional pipeline identifier for debugging
            
        Design Decision: Dependency injection allows different combinations
        of authenticators, validators, and processors while maintaining
        the same pipeline interface. This supports different input sources
        with different requirements.
        """
        self.authenticator = authenticator
        self.validator = validator
        self.processor = processor
        self.pipeline_id = pipeline_id or f"pipeline_{int(time.time())}"
    
    @abstractmethod
    async def process(
        self, 
        raw_input: Any,
        credentials: SourceCredentials,
        request_context: Optional[Dict[str, Any]] = None
    ) -> PipelineResult:
        """
        Process raw input through the complete pipeline.
        
        This is the main entry point for input processing. It coordinates:
        1. Authentication and permission resolution
        2. Input validation and safety checking
        3. Content normalization and event creation
        
        Args:
            raw_input: Raw input from the source
            credentials: Source credentials for authentication
            request_context: Optional additional context (headers, etc.)
            
        Returns:
            PipelineResult with JanusEvent or error information
            
        Design Decision: Return PipelineResult rather than just JanusEvent
        because callers often need the processing metadata for logging,
        monitoring, and debugging.
        
        Pipeline Order (FIXED for security):
        1. Authentication: Verify credentials and establish permissions
        2. Validation: Check format and safety (no permission guessing)
        3. Processing: Normalize content and create JanusEvent
        
        Failure Handling: Stop at first failure and return detailed error
        information including which stage failed and why.
        """
        pass
    
    async def create_pipeline_result(self, pipeline_id: str) -> PipelineResult:
        """
        Create initial pipeline result object.
        
        Args:
            pipeline_id: Unique identifier for this pipeline run
            
        Returns:
            Initialized PipelineResult
            
        Helper method for consistent pipeline result creation.
        """
        return PipelineResult(
            pipeline_id=pipeline_id,
            started_at=datetime.utcnow(),
            stage_timings={},
            stages_completed=[]
        )
    
    async def execute_authentication_stage(
        self,
        credentials: SourceCredentials,
        request_context: Dict[str, Any],
        result: PipelineResult
    ) -> Result[AuthContext, PipelineError]:
        """
        Execute authentication stage with timing and error handling.
        
        Args:
            credentials: Source credentials
            request_context: Request context
            result: Pipeline result to update
            
        Returns:
            Result containing AuthContext or pipeline error
            
        Design Decision: Separate method for each stage allows consistent
        error handling, timing, and result tracking across all stages.
        """
        stage_start = time.time()
        
        try:
            auth_result = await self.authenticator.authenticate(credentials, request_context)
            
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["authentication"] = stage_time
            
            if auth_result.is_success:
                result.stages_completed.append("authentication")
                return Result.success(auth_result.unwrap())
            else:
                auth_error = auth_result.unwrap_error()
                pipeline_error = PipelineError(
                    error_type="pipeline_error",
                    message=f"Authentication failed: {auth_error.message}",
                    component="InputPipeline",
                    failed_stage="authentication",
                    pipeline_context={"pipeline_id": result.pipeline_id},
                    stage_errors=[auth_error]
                )
                return Result.error(pipeline_error)
                
        except Exception as e:
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["authentication"] = stage_time
            
            pipeline_error = PipelineError(
                error_type="pipeline_error",
                message=f"Authentication stage failed: {e}",
                component="InputPipeline",
                failed_stage="authentication",
                pipeline_context={"pipeline_id": result.pipeline_id, "exception": str(e)}
            )
            return Result.error(pipeline_error)
    
    async def execute_validation_stage(
        self,
        raw_input: Any,
        auth_context: AuthContext,
        result: PipelineResult
    ) -> Result[ValidatedInput, PipelineError]:
        """
        Execute validation stage with timing and error handling.
        
        Args:
            raw_input: Raw input to validate
            auth_context: Authentication context
            result: Pipeline result to update
            
        Returns:
            Result containing ValidatedInput or pipeline error
        """
        stage_start = time.time()
        
        try:
            validation_result = await self.validator.validate(raw_input, auth_context)
            
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["validation"] = stage_time
            
            if validation_result.is_success:
                result.stages_completed.append("validation")
                return Result.success(validation_result.unwrap())
            else:
                validation_error = validation_result.unwrap_error()
                pipeline_error = PipelineError(
                    error_type="pipeline_error",
                    message=f"Validation failed: {validation_error.message}",
                    component="InputPipeline", 
                    failed_stage="validation",
                    pipeline_context={"pipeline_id": result.pipeline_id},
                    stage_errors=[validation_error]
                )
                return Result.error(pipeline_error)
                
        except Exception as e:
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["validation"] = stage_time
            
            pipeline_error = PipelineError(
                error_type="pipeline_error",
                message=f"Validation stage failed: {e}",
                component="InputPipeline",
                failed_stage="validation", 
                pipeline_context={"pipeline_id": result.pipeline_id, "exception": str(e)}
            )
            return Result.error(pipeline_error)
    
    async def execute_processing_stage(
        self,
        validated_input: ValidatedInput,
        auth_context: AuthContext,
        result: PipelineResult
    ) -> Result[JanusEvent, PipelineError]:
        """
        Execute processing stage with timing and error handling.
        
        Args:
            validated_input: Validated input
            auth_context: Authentication context
            result: Pipeline result to update
            
        Returns:
            Result containing JanusEvent or pipeline error
        """
        stage_start = time.time()
        
        try:
            processing_result = await self.processor.process(validated_input, auth_context)
            
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["processing"] = stage_time
            
            if processing_result.is_success:
                result.stages_completed.append("processing")
                return Result.success(processing_result.unwrap())
            else:
                processing_error = processing_result.unwrap_error()
                pipeline_error = PipelineError(
                    error_type="pipeline_error",
                    message=f"Processing failed: {processing_error.message}",
                    component="InputPipeline",
                    failed_stage="processing",
                    pipeline_context={"pipeline_id": result.pipeline_id},
                    stage_errors=[processing_error]
                )
                return Result.error(pipeline_error)
                
        except Exception as e:
            stage_time = int((time.time() - stage_start) * 1000)
            result.stage_timings["processing"] = stage_time
            
            pipeline_error = PipelineError(
                error_type="pipeline_error",
                message=f"Processing stage failed: {e}",
                component="InputPipeline",
                failed_stage="processing",
                pipeline_context={"pipeline_id": result.pipeline_id, "exception": str(e)}
            )
            return Result.error(pipeline_error)
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all pipeline components.
        
        Returns:
            Dictionary of component health status
            
        This checks the health of all composed components to ensure
        the pipeline can process input successfully.
        """
        health_status = {}
        
        try:
            health_status["authenticator"] = await self.authenticator.health_check()
        except Exception:
            health_status["authenticator"] = False
        
        try:
            validator_health = await self.validator.health_check()
            health_status.update({f"validator_{k}": v for k, v in validator_health.items()})
        except Exception:
            health_status["validator"] = False
        
        try:
            processor_health = await self.processor.health_check()
            health_status.update({f"processor_{k}": v for k, v in processor_health.items()})
        except Exception:
            health_status["processor"] = False
        
        return health_status
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about this pipeline configuration.
        
        Returns:
            Dictionary with pipeline configuration details
            
        Useful for debugging and monitoring to understand how
        the pipeline is configured.
        """
        return {
            "pipeline_id": self.pipeline_id,
            "authenticator_type": self.authenticator.__class__.__name__,
            "validator_type": self.validator.__class__.__name__,
            "processor_type": self.processor.__class__.__name__,
            "source_type": self.authenticator.source_type,
            "created_at": datetime.utcnow().isoformat()
        }