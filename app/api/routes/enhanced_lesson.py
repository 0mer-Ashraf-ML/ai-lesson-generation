from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, ErrorResponse
from app.services.enhanced_lesson_service import enhanced_lesson_service
from app.utils.exceptions import SkillSelectionError, LLMGenerationError, DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/lessons", tags=["enhanced-lessons"])


async def get_current_user() -> Optional[str]:
    """Get current user ID - simplified for MVP"""
    return "mvp-user-123"


@router.post("/generatePlan", response_model=LessonResponse)
async def generate_enhanced_lesson_plan(
    request: LessonRequest,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Generate a new lesson plan using enhanced Structural Learning framework
    
    This endpoint uses the full framework metadata including:
    - Framework-aware skill selection based on subject and difficulty
    - Complete block type definitions (MapIt, SayIt, BuildIt)
    - Subject-specific guidance and vocabulary
    - Difficulty-appropriate complexity levels
    - Comprehensive pedagogical scaffolding
    
    Args:
        request: Lesson generation parameters
        current_user: Current user ID (from auth)
        
    Returns:
        Generated lesson plan with framework-enhanced blocks
    """
    try:
        logger.info(
            "Enhanced lesson generation request received",
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            difficulty=request.difficulty,
            user_id=current_user,
            framework_version="enhanced"
        )
        
        # Generate the lesson using enhanced service
        lesson_response = await enhanced_lesson_service.generate_lesson(
            request=request,
            user_id=current_user
        )
        
        # Add enhancement indicator to response
        lesson_response.metadata.framework_enhanced = True
        
        return lesson_response
        
    except SkillSelectionError as e:
        logger.error("Enhanced skill selection error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill selection failed: {str(e)}"
        )
        
    except LLMGenerationError as e:
        logger.error("Enhanced LLM generation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Content generation failed: {str(e)}"
        )
        
    except DatabaseError as e:
        logger.error("Database error in enhanced service", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save lesson plan"
        )
        
    except Exception as e:
        logger.error("Unexpected error in enhanced lesson generation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/framework-info")
async def get_framework_info():
    """
    Get information about the enhanced Structural Learning framework
    
    Returns metadata about available skills, block types, and framework structure
    """
    try:
        from app.core.skills.enhanced_metadata import enhanced_skill_metadata
        
        # Get framework structure info
        skills_by_color = {}
        for color, color_data in enhanced_skill_metadata._skills_data.items():
            skills_by_color[color] = {
                "category": color_data["category"],
                "description": color_data["description"],
                "skills": [skill["skill"] for skill in color_data["skills"]]
            }
        
        block_types = list(enhanced_skill_metadata._blocks_data.keys()) if enhanced_skill_metadata._blocks_data else []
        
        return {
            "framework_version": "Enhanced v1.0",
            "colors": skills_by_color,
            "block_types": block_types,
            "total_skills": sum(len(color_data["skills"]) for color_data in enhanced_skill_metadata._skills_data.values()),
            "enhancements": [
                "Subject-specific skill selection",
                "Difficulty-appropriate complexity levels", 
                "Complete block type definitions",
                "Framework-guided prompt generation",
                "Pedagogical scaffolding integration"
            ]
        }
        
    except Exception as e:
        logger.error("Error getting framework info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve framework information"
        )


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_enhanced_lesson(
    lesson_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Retrieve a specific lesson by ID
    """
    try:
        lesson = await enhanced_lesson_service.get_lesson(lesson_id, current_user)
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found or access denied"
            )
        
        return lesson
        
    except Exception as e:
        logger.error("Error retrieving enhanced lesson", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lesson"
        )


@router.get("/", response_model=List[LessonResponse])
async def get_user_enhanced_lessons(
    limit: int = 50,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Get all lessons for the current user
    """
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        lessons = await enhanced_lesson_service.get_user_lessons(current_user, limit)
        
        return lessons
        
    except Exception as e:
        logger.error("Error retrieving user enhanced lessons", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lessons"
        )