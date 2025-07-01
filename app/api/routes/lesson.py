from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models.requests import LessonRequest, SequenceRequest
from app.models.responses import LessonResponse, HealthResponse
from app.services.time_aware_lesson_service import time_aware_lesson_service
from app.dependencies import get_authenticated_user, get_current_user
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.post("/generatePlan", response_model=LessonResponse)
async def generate_lesson_plan(
    request: LessonRequest,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Generate an AI lesson plan using time-aware and adaptive scaffolding
    
    Enhanced Features:
    - Intelligent scaffolding decisions (full activities vs. discussion prompts)
    - Time-aware planning when available_time_minutes is provided
    - Automatic skill card attachment
    - RAG-enhanced skill selection
    - Cross-activity variety management
    """
    try:
        logger.info(
            "Lesson generation request received",
            user_id=current_user,
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            available_time=request.available_time_minutes,
            time_flexibility=request.time_flexibility
        )
        
        # Generate adaptive lesson
        lesson_response = await time_aware_lesson_service.generate_adaptive_lesson(
            request=request,
            user_id=current_user
        )
        
        logger.info(
            "Lesson generated successfully",
            lesson_id=lesson_response.lesson_id,
            blocks_count=len(lesson_response.blocks),
            estimated_duration=lesson_response.metadata.estimated_duration
        )
        
        return lesson_response
        
    except Exception as e:
        logger.error("Failed to generate lesson plan", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate lesson plan")


@router.post("/generateSequence", response_model=List[LessonResponse])
async def generate_lesson_sequence(
    request: SequenceRequest,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Generate a sequence of related lessons with cross-lesson variety
    
    Features:
    - Progressive difficulty across lessons
    - Variety in scaffolding types across the sequence
    - Consistent topic but varied approaches
    """
    try:
        logger.info(
            "Lesson sequence generation request",
            user_id=current_user,
            topic=request.base_request.topic,
            sequence_length=request.sequence_length
        )
        
        lessons = await time_aware_lesson_service.generate_lesson_sequence(
            base_request=request.base_request,
            sequence_length=request.sequence_length,
            user_id=current_user
        )
        
        logger.info(
            "Lesson sequence generated successfully",
            sequence_length=len(lessons),
            lesson_ids=[lesson.lesson_id for lesson in lessons]
        )
        
        return lessons
        
    except Exception as e:
        logger.error("Failed to generate lesson sequence", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate lesson sequence")


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Retrieve a specific lesson by ID
    
    Returns the complete lesson with all blocks, resources, and metadata
    """
    try:
        lesson = await time_aware_lesson_service.get_lesson(lesson_id, current_user)
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        return lesson
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve lesson", error=str(e), lesson_id=lesson_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve lesson")


@router.get("/", response_model=List[LessonResponse])
async def get_user_lessons(
    current_user: str = Depends(get_authenticated_user),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of lessons to return")
):
    """
    Get all lessons for the authenticated user
    
    Returns lessons ordered by creation date (newest first)
    """
    try:
        lessons = await time_aware_lesson_service.get_user_lessons(current_user, limit)
        
        logger.info("Retrieved user lessons", user_id=current_user, count=len(lessons))
        
        return lessons
        
    except Exception as e:
        logger.error("Failed to retrieve user lessons", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail="Failed to retrieve lessons")


@router.get("/analytics/summary")
async def get_lesson_analytics(
    current_user: str = Depends(get_authenticated_user)
):
    """
    Get analytics summary for user's lessons
    
    Returns:
    - Total lessons created
    - Most used subjects
    - Most used thinking skills
    - Average difficulty levels
    - Time usage patterns
    """
    try:
        # Get user's lessons
        lessons = await time_aware_lesson_service.get_user_lessons(current_user, limit=1000)
        
        if not lessons:
            return {
                "total_lessons": 0,
                "subjects": {},
                "thinking_skills": {},
                "difficulty_distribution": {},
                "time_patterns": {},
                "scaffolding_preferences": {}
            }
        
        # Analyze lessons
        analytics = {
            "total_lessons": len(lessons),
            "subjects": _analyze_subjects(lessons),
            "thinking_skills": _analyze_thinking_skills(lessons),
            "difficulty_distribution": _analyze_difficulty(lessons),
            "time_patterns": _analyze_time_patterns(lessons),
            "scaffolding_preferences": _analyze_scaffolding(lessons)
        }
        
        logger.info("Generated lesson analytics", user_id=current_user, total_lessons=len(lessons))
        
        return analytics
        
    except Exception as e:
        logger.error("Failed to generate analytics", error=str(e), user_id=current_user)
        raise HTTPException(status_code=500, detail="Failed to generate analytics")


@router.post("/quickGenerate", response_model=LessonResponse)
async def quick_generate_lesson(
    topic: str = Query(..., description="Lesson topic"),
    grade: str = Query(..., description="Grade level"),
    subject: str = Query(..., description="Subject area"),
    time_minutes: int = Query(45, ge=10, le=120, description="Available time in minutes"),
    difficulty: float = Query(0.5, ge=0.0, le=1.0, description="Difficulty level"),
    current_user: Optional[str] = Depends(get_current_user)
):
    """
    Quick lesson generation with minimal parameters
    
    Automatically selects optimal settings for time and complexity
    """
    try:
        # Create simplified request
        request = LessonRequest(
            topic=topic,
            grade=grade,
            subject=subject,
            curriculum="General",  # Default curriculum
            difficulty=difficulty,
            step_count=3,  # Default step count
            available_time_minutes=time_minutes,
            time_flexibility="moderate",
            prefer_variety=True
        )
        
        lesson_response = await time_aware_lesson_service.generate_adaptive_lesson(
            request=request,
            user_id=current_user
        )
        
        logger.info("Quick lesson generated", topic=topic, grade=grade, time_minutes=time_minutes)
        
        return lesson_response
        
    except Exception as e:
        logger.error("Failed to generate quick lesson", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate lesson")


# Helper functions for analytics
def _analyze_subjects(lessons: List[LessonResponse]) -> dict:
    """Analyze subject distribution"""
    subjects = {}
    for lesson in lessons:
        subject = lesson.subject
        subjects[subject] = subjects.get(subject, 0) + 1
    return dict(sorted(subjects.items(), key=lambda x: x[1], reverse=True))


def _analyze_thinking_skills(lessons: List[LessonResponse]) -> dict:
    """Analyze thinking skills usage"""
    skills = {}
    for lesson in lessons:
        for skill_name in lesson.metadata.skills_used:
            skills[skill_name] = skills.get(skill_name, 0) + 1
    return dict(sorted(skills.items(), key=lambda x: x[1], reverse=True)[:10])


def _analyze_difficulty(lessons: List[LessonResponse]) -> dict:
    """Analyze difficulty distribution"""
    difficulties = {"Easy (0.0-0.3)": 0, "Medium (0.3-0.7)": 0, "Hard (0.7-1.0)": 0}
    
    for lesson in lessons:
        if lesson.difficulty <= 0.3:
            difficulties["Easy (0.0-0.3)"] += 1
        elif lesson.difficulty <= 0.7:
            difficulties["Medium (0.3-0.7)"] += 1
        else:
            difficulties["Hard (0.7-1.0)"] += 1
    
    return difficulties


def _analyze_time_patterns(lessons: List[LessonResponse]) -> dict:
    """Analyze time usage patterns"""
    time_patterns = {
        "short_lessons": 0,    # < 30 min
        "medium_lessons": 0,   # 30-60 min  
        "long_lessons": 0,     # > 60 min
        "average_duration": 0
    }
    
    total_duration = 0
    duration_count = 0
    
    for lesson in lessons:
        duration_str = lesson.metadata.estimated_duration
        if "minutes" in duration_str:
            try:
                duration = int(duration_str.split()[0])
                total_duration += duration
                duration_count += 1
                
                if duration < 30:
                    time_patterns["short_lessons"] += 1
                elif duration <= 60:
                    time_patterns["medium_lessons"] += 1
                else:
                    time_patterns["long_lessons"] += 1
            except:
                pass
    
    if duration_count > 0:
        time_patterns["average_duration"] = round(total_duration / duration_count, 1)
    
    return time_patterns


def _analyze_scaffolding(lessons: List[LessonResponse]) -> dict:
    """Analyze scaffolding type preferences"""
    scaffolding = {"MapIt": 0, "SayIt": 0, "BuildIt": 0, "Prompt": 0}
    
    for lesson in lessons:
        for block in lesson.blocks:
            block_type = block.type
            if block_type in scaffolding:
                scaffolding[block_type] += 1
    
    return scaffolding