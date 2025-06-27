from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, ErrorResponse
from app.services.lesson_service import lesson_service
from app.utils.exceptions import SkillSelectionError, LLMGenerationError, DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/lessons", tags=["lessons"])


# For MVP, we'll use a simple user ID system
# In production, this would be replaced with proper JWT authentication
async def get_current_user() -> Optional[str]:
    """Get current user ID - simplified for MVP"""
    # For MVP, return a default user ID
    # In production, this would extract user from JWT token
    return "mvp-user-123"


@router.post("/generatePlan", response_model=LessonResponse)
async def generate_lesson_plan(
    request: LessonRequest,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Generate a new lesson plan based on teacher inputs
    
    Args:
        request: Lesson generation parameters
        current_user: Current user ID (from auth)
        
    Returns:
        Generated lesson plan with blocks
    """
    try:
        logger.info(
            "Lesson generation request received",
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            user_id=current_user
        )
        
        # Generate the lesson
        lesson_response = await lesson_service.generate_lesson(
            request=request,
            user_id=current_user
        )
        
        return lesson_response
        
    except SkillSelectionError as e:
        logger.error("Skill selection error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill selection failed: {str(e)}"
        )
        
    except LLMGenerationError as e:
        logger.error("LLM generation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Content generation failed: {str(e)}"
        )
        
    except DatabaseError as e:
        logger.error("Database error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save lesson plan"
        )
        
    except Exception as e:
        logger.error("Unexpected error in lesson generation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Retrieve a specific lesson by ID
    
    Args:
        lesson_id: The lesson ID to retrieve
        current_user: Current user ID (from auth)
        
    Returns:
        The lesson plan if found and user has access
    """
    try:
        lesson = await lesson_service.get_lesson(lesson_id, current_user)
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found or access denied"
            )
        
        return lesson
        
    except DatabaseError as e:
        logger.error("Database error retrieving lesson", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lesson"
        )
        
    except Exception as e:
        logger.error("Unexpected error retrieving lesson", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/", response_model=List[LessonResponse])
async def get_user_lessons(
    limit: int = 50,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Get all lessons for the current user
    
    Args:
        limit: Maximum number of lessons to return (default 50)
        current_user: Current user ID (from auth)
        
    Returns:
        List of user's lesson plans
    """
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        lessons = await lesson_service.get_user_lessons(current_user, limit)
        
        return lessons
        
    except DatabaseError as e:
        logger.error("Database error retrieving user lessons", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lessons"
        )
        
    except Exception as e:
        logger.error("Unexpected error retrieving user lessons", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


# Future extension endpoints (placeholder for easy addition)

@router.post("/{lesson_id}/regenerate", response_model=LessonResponse)
async def regenerate_lesson_plan(
    lesson_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Regenerate an existing lesson plan (future feature)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Lesson regeneration not yet implemented"
    )


@router.post("/{lesson_id}/blocks/{block_id}/regenerate")
async def regenerate_block(
    lesson_id: str,
    block_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Regenerate a specific block within a lesson (future feature)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Block regeneration not yet implemented"
    )


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Delete a lesson plan (future feature)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Lesson deletion not yet implemented"
    )