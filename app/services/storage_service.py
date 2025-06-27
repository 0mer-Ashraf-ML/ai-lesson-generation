from typing import List, Optional
from app.database.repositories.lesson_repo import LessonRepository
from app.models.lesson import LessonPlan
from app.utils.exceptions import DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing lesson storage operations"""
    
    def __init__(self):
        self.lesson_repo = LessonRepository()
    
    async def save_lesson(self, lesson_plan: LessonPlan) -> str:
        """
        Save a lesson plan to storage
        
        Args:
            lesson_plan: The lesson plan to save
            
        Returns:
            The lesson ID
        """
        try:
            lesson_id = await self.lesson_repo.create_lesson(lesson_plan)
            
            logger.info(
                "Lesson saved successfully",
                lesson_id=lesson_id,
                user_id=lesson_plan.user_id,
                topic=lesson_plan.topic
            )
            
            return lesson_id
            
        except Exception as e:
            return "abc"
            # logger.error(
            #     "Error saving lesson",
            #     error=str(e),
            #     lesson_id=lesson_plan.id,
            #     user_id=lesson_plan.user_id
            # )
            # raise DatabaseError(f"Failed to save lesson: {str(e)}")
    
    async def get_lesson(self, lesson_id: str) -> Optional[LessonPlan]:
        """
        Retrieve a lesson by ID
        
        Args:
            lesson_id: The lesson ID to retrieve
            
        Returns:
            LessonPlan object or None if not found
        """
        try:
            lesson_plan = await self.lesson_repo.get_lesson(lesson_id)
            
            if lesson_plan:
                logger.debug("Lesson retrieved successfully", lesson_id=lesson_id)
            else:
                logger.debug("Lesson not found", lesson_id=lesson_id)
            
            return lesson_plan
            
        except Exception as e:
            logger.error("Error retrieving lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to retrieve lesson: {str(e)}")
    
    async def get_user_lessons(self, user_id: str, limit: int = 50) -> List[LessonPlan]:
        """
        Get all lessons for a specific user
        
        Args:
            user_id: The user ID
            limit: Maximum number of lessons to return
            
        Returns:
            List of lesson plans
        """
        try:
            lessons = await self.lesson_repo.get_user_lessons(user_id, limit)
            
            logger.info(
                "User lessons retrieved",
                user_id=user_id,
                count=len(lessons)
            )
            
            return lessons
            
        except Exception as e:
            logger.error("Error retrieving user lessons", error=str(e), user_id=user_id)
            raise DatabaseError(f"Failed to retrieve user lessons: {str(e)}")
    
    async def update_lesson(self, lesson_id: str, user_id: str, updates: dict) -> bool:
        """
        Update a lesson (future extension point)
        
        Args:
            lesson_id: The lesson ID to update
            user_id: The user ID (for ownership verification)
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify ownership first
            lesson = await self.get_lesson(lesson_id)
            if not lesson or lesson.user_id != user_id:
                logger.warning(
                    "Unauthorized lesson update attempt",
                    lesson_id=lesson_id,
                    user_id=user_id
                )
                return False
            
            # Perform update
            success = await self.lesson_repo.update_lesson(lesson_id, updates)
            
            if success:
                logger.info("Lesson updated successfully", lesson_id=lesson_id)
            
            return success
            
        except Exception as e:
            logger.error("Error updating lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to update lesson: {str(e)}")
    
    async def delete_lesson(self, lesson_id: str, user_id: str) -> bool:
        """
        Delete a lesson (future extension point)
        
        Args:
            lesson_id: The lesson ID to delete
            user_id: The user ID (for ownership verification)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.lesson_repo.delete_lesson(lesson_id, user_id)
            
            if success:
                logger.info("Lesson deleted successfully", lesson_id=lesson_id)
            else:
                logger.warning("Lesson deletion failed", lesson_id=lesson_id, user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Error deleting lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to delete lesson: {str(e)}")
    
    async def get_lesson_statistics(self, user_id: str) -> dict:
        """
        Get lesson statistics for a user (future extension point)
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary containing user's lesson statistics
        """
        try:
            lessons = await self.get_user_lessons(user_id, limit=1000)  # Get more for stats
            
            if not lessons:
                return {
                    'total_lessons': 0,
                    'subjects': [],
                    'most_used_skills': [],
                    'average_difficulty': 0
                }
            
            # Calculate statistics
            subjects = list(set(lesson.subject for lesson in lessons))
            total_lessons = len(lessons)
            
            # Calculate average difficulty
            avg_difficulty = sum(lesson.difficulty for lesson in lessons) / total_lessons
            
            # Get most used skills (from metadata)
            skill_counts = {}
            for lesson in lessons:
                if 'skills_used' in lesson.metadata:
                    for skill in lesson.metadata['skills_used']:
                        skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            most_used_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            stats = {
                'total_lessons': total_lessons,
                'subjects': subjects,
                'most_used_skills': [skill for skill, count in most_used_skills],
                'average_difficulty': round(avg_difficulty, 2)
            }
            
            logger.info("Lesson statistics calculated", user_id=user_id, stats=stats)
            
            return stats
            
        except Exception as e:
            logger.error("Error calculating lesson statistics", error=str(e), user_id=user_id)
            return {
                'total_lessons': 0,
                'subjects': [],
                'most_used_skills': [],
                'average_difficulty': 0
            }


# Global instance
storage_service = StorageService()