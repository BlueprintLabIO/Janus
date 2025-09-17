"""
Input Authentication Interfaces

Handles credential verification and permission resolution for input sources.

Design Philosophy:
- Security by Default: All requests must be authenticated
- Per-Request Auth: No cached credentials, verify every time for security
- Permission Intersection: Final permissions = credential_permissions ∩ user_permissions
- Fail Fast: Authentication failures stop processing immediately
- Auditability: Full audit trail of authentication decisions

Key Insight: Authentication happens BEFORE validation/processing to prevent
unauthenticated users from consuming system resources.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...core import Result, ProcessingError
from .models import SourceCredentials, AuthContext


class AuthenticationError(ProcessingError):
    """
    Specific error type for authentication failures.
    
    Design Decision: Use specific error types for different failure modes.
    This allows callers to handle auth failures differently from other errors.
    """
    error_type: str = "authentication_error"
    
    # Additional auth-specific fields
    auth_failure_reason: str = ""
    retry_possible: bool = False
    credential_source: Optional[str] = None


class CredentialValidator(ABC):
    """
    Validates raw credentials for a specific source type.
    
    Responsibility: Check that credentials are structurally valid and not expired.
    Does NOT check permissions - that's the PermissionResolver's job.
    
    Design Decision: Separate credential validation from permission resolution.
    This allows credential validation to be fast and permission resolution to be complex.
    
    Examples:
    - API Key: Check format, not revoked, not expired
    - Slack Token: Verify OAuth token, check workspace validity
    - Webhook: Verify signature matches expected format
    """
    
    @property
    @abstractmethod
    def supported_source_type(self) -> str:
        """
        Source type this validator handles.
        
        Returns: Source type string (e.g., "api", "slack", "webhook")
        """
        pass
    
    @abstractmethod
    async def validate_credential_format(
        self, 
        credentials: SourceCredentials
    ) -> Result[bool, AuthenticationError]:
        """
        Validate credential structure and basic validity.
        
        This should be FAST - just check format, expiration, basic validity.
        No network calls, no complex logic, no permission checking.
        
        Args:
            credentials: Raw credentials to validate
            
        Returns:
            Result indicating if credentials are structurally valid
            
        Examples:
            - API key has proper format (sk-...)
            - Slack token is valid OAuth format
            - Webhook secret is not empty
            
        Should NOT:
            - Make network calls to verify with external services
            - Check permissions or user access
            - Perform complex business logic
        """
        pass
    
    @abstractmethod 
    async def extract_user_identity(
        self, 
        credentials: SourceCredentials,
        request_context: Dict[str, Any]
    ) -> Result[str, AuthenticationError]:
        """
        Extract user identity from credentials and request context.
        
        Args:
            credentials: Valid credentials
            request_context: Additional context from the request (headers, body, etc.)
            
        Returns:
            Result containing user_id or authentication error
            
        Design Decision: User identity extraction is separate from validation
        because some sources embed user info in credentials (API key) while
        others require parsing request context (webhook payload).
        
        Examples:
            - API key: user_id embedded in key metadata
            - Slack: user_id from message payload
            - Webhook: user_id from signed payload
        """
        pass
    
    async def get_credential_metadata(
        self, 
        credentials: SourceCredentials
    ) -> Dict[str, Any]:
        """
        Extract metadata from credentials (optional override).
        
        Returns metadata about the credential itself (not the user).
        Useful for audit logging and debugging.
        
        Args:
            credentials: Valid credentials
            
        Returns:
            Metadata dictionary
            
        Examples:
            {"key_type": "service", "created_at": "2024-01-01", "scope": "read"}
        """
        return {
            "source_type": credentials.source_type,
            "source_id": credentials.source_id,
            "validated_at": datetime.utcnow().isoformat()
        }


class PermissionResolver(ABC):
    """
    Resolves final permissions for an authenticated user.
    
    Responsibility: Determine what the user is allowed to do.
    This is where the permission intersection logic lives.
    
    Design Decision: Separate from credential validation because permission 
    resolution can be complex (database lookups, role calculations, etc.)
    while credential validation should be fast.
    
    Key Algorithm: final_permissions = credential_permissions ∩ user_permissions
    """
    
    @abstractmethod
    async def resolve_user_permissions(
        self, 
        user_id: str, 
        source_type: str
    ) -> Result[List[str], AuthenticationError]:
        """
        Get permissions assigned to a specific user from a specific source.
        
        Args:
            user_id: Authenticated user identifier
            source_type: Type of source requesting permissions
            
        Returns:
            Result containing list of permissions or error
            
        Implementation Notes:
            - May require database/cache lookups
            - Should handle user not found gracefully
            - Can be expensive - called once per request
            
        Examples:
            User "john_doe" from "slack" source might have:
            ["chat", "tools.calculator", "memory.read"]
            
            User "admin_user" from "api" source might have:
            ["chat", "tools.*", "memory.*", "admin.*"]
        """
        pass
    
    async def compute_final_permissions(
        self, 
        credential_permissions: List[str],
        user_permissions: List[str]
    ) -> List[str]:
        """
        Compute intersection of credential and user permissions.
        
        Args:
            credential_permissions: Permissions granted by the credential
            user_permissions: Permissions assigned to the user
            
        Returns:
            Final permissions (intersection of both lists)
            
        Design Decision: Use intersection (AND) rather than union (OR) for security.
        Both the credential AND the user must have a permission for it to be granted.
        
        Algorithm:
            1. Handle wildcard permissions (tools.* matches tools.calculator)
            2. Compute intersection
            3. Return sorted list for consistency
            
        Examples:
            credential_permissions = ["chat", "tools.*"]
            user_permissions = ["chat", "tools.calculator", "memory.read"]
            result = ["chat", "tools.calculator"]  # intersection
        """
        # Handle wildcard expansion
        expanded_credential_perms = self._expand_wildcards(
            credential_permissions, 
            user_permissions
        )
        
        # Compute intersection
        final_perms = list(set(expanded_credential_perms) & set(user_permissions))
        
        # Sort for consistency in testing/debugging
        return sorted(final_perms)
    
    def _expand_wildcards(
        self, 
        wildcard_perms: List[str], 
        target_perms: List[str]
    ) -> List[str]:
        """
        Expand wildcard permissions against target permission list.
        
        Args:
            wildcard_perms: Permissions that may contain wildcards
            target_perms: Specific permissions to match against
            
        Returns:
            Expanded permission list
            
        Example:
            wildcard_perms = ["tools.*", "chat"]
            target_perms = ["tools.calculator", "tools.time", "chat", "memory.read"]
            result = ["tools.calculator", "tools.time", "chat"]
        """
        expanded = []
        
        for perm in wildcard_perms:
            if perm.endswith(".*"):
                # Wildcard permission - find all matching target permissions
                prefix = perm[:-2]  # Remove ".*"
                matching = [p for p in target_perms if p.startswith(f"{prefix}.")]
                expanded.extend(matching)
            else:
                # Exact permission
                expanded.append(perm)
        
        return list(set(expanded))  # Remove duplicates


class InputAuthenticator(ABC):
    """
    Main authentication interface that orchestrates credential validation and permission resolution.
    
    Responsibility: Coordinate the authentication process and produce AuthContext.
    This is the main interface that input pipelines interact with.
    
    Design Decision: Compose CredentialValidator + PermissionResolver rather than
    inheriting from them. This allows flexible authentication strategies.
    """
    
    def __init__(
        self, 
        credential_validator: CredentialValidator,
        permission_resolver: PermissionResolver
    ):
        """
        Initialize with composed validation and permission resolution strategies.
        
        Args:
            credential_validator: Handles credential format validation
            permission_resolver: Handles permission calculation
            
        Design Decision: Dependency injection allows different authentication
        strategies for different source types while maintaining the same interface.
        """
        self.credential_validator = credential_validator
        self.permission_resolver = permission_resolver
    
    @abstractmethod
    async def authenticate(
        self, 
        credentials: SourceCredentials,
        request_context: Dict[str, Any]
    ) -> Result[AuthContext, AuthenticationError]:
        """
        Perform complete authentication and return auth context.
        
        This is the main entry point for authentication. It orchestrates:
        1. Credential validation
        2. User identity extraction
        3. Permission resolution
        4. AuthContext creation
        
        Args:
            credentials: Source credentials to authenticate
            request_context: Additional request context (headers, payload, etc.)
            
        Returns:
            Result containing AuthContext or authentication error
            
        Design Decision: Return AuthContext rather than just "success/failure"
        because callers need the permission and user information for processing.
        
        Error Handling: Any authentication failure should result in a clear error
        that doesn't leak information about valid vs invalid credentials.
        """
        pass
    
    async def create_auth_context(
        self,
        user_id: str,
        credentials: SourceCredentials,
        final_permissions: List[str],
        auth_metadata: Dict[str, Any]
    ) -> AuthContext:
        """
        Create AuthContext from authentication results.
        
        Args:
            user_id: Authenticated user identifier
            credentials: Original credentials
            final_permissions: Computed final permissions
            auth_metadata: Authentication process metadata
            
        Returns:
            Complete AuthContext
            
        Design Decision: Separate method for AuthContext creation allows
        easier testing and customization of context creation logic.
        """
        return AuthContext(
            user_id=user_id,
            source_type=credentials.source_type,
            source_id=credentials.source_id,
            granted_permissions=final_permissions,
            authenticated_at=datetime.utcnow(),
            expires_at=credentials.expires_at,
            auth_metadata=auth_metadata
        )
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Source type this authenticator handles."""
        pass
    
    async def health_check(self) -> bool:
        """
        Check if authentication services are healthy.
        
        Returns:
            True if authentication can be performed
            
        This should check:
        - Database connectivity (if needed for user lookup)
        - External service availability (if needed for credential verification)
        - Internal component health
        """
        return True