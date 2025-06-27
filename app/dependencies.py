from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme for future JWT implementation
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Get the current authenticated user
    
    For MVP: Returns a default user ID
    For Production: Would validate JWT token and return user ID
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        User ID string or None if not authenticated
    """
    # MVP Implementation - return default user
    # In production, this would:
    # 1. Validate the JWT token from credentials.credentials
    # 2. Extract user ID from the token
    # 3. Return user ID or raise HTTPException for invalid tokens
    
    if not credentials:
        # For MVP, allow unauthenticated access with default user
        logger.debug("No credentials provided, using default MVP user")
        return "mvp-user-123"
    
    # Future JWT validation would go here
    # For now, just log the token presence
    logger.debug("Credentials present but JWT validation not implemented")
    return "mvp-user-123"


async def get_authenticated_user(
    current_user: Optional[str] = Depends(get_current_user)
) -> str:
    """
    Require authentication - raises exception if user not authenticated
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return current_user


# Future extension points for different permission levels
class PermissionChecker:
    """Future class for handling different permission levels"""
    
    def __init__(self, required_permissions: list = None):
        self.required_permissions = required_permissions or []
    
    async def __call__(self, current_user: str = Depends(get_authenticated_user)) -> str:
        """Check if user has required permissions"""
        # For MVP, all authenticated users have all permissions
        # In production, this would check user roles/permissions
        return current_user


# Pre-configured permission checkers for common use cases
require_teacher_permissions = PermissionChecker(["create_lessons", "view_lessons"])
require_admin_permissions = PermissionChecker(["admin_access"])


# Database dependency helpers
async def get_lesson_service():
    """Get lesson service instance"""
    from app.services.lesson_service import lesson_service
    return lesson_service


async def get_storage_service():
    """Get storage service instance"""
    from app.services.storage_service import storage_service
    return storage_service