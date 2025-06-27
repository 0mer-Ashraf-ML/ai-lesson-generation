from typing import List, Optional, Dict, Any
from app.database.supabase_client import supabase_client
from app.models.lesson import LessonPlan
from app.utils.exceptions import DatabaseError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LessonRepository:
    """Repository for lesson CRUD operations"""
    
    def __init__(self):
        self.client = supabase_client.client
    
    async def create_lesson(self, lesson: LessonPlan) -> str:
        """Create a new lesson in the database"""
        try:
            lesson_data = {
                'id': lesson.id,
                'user_id': lesson.user_id,
                'title': lesson.title,
                'topic': lesson.topic,
                'grade': lesson.grade,
                'subject': lesson.subject,
                'curriculum': lesson.curriculum,
                'difficulty': lesson.difficulty,
                'blocks': lesson.blocks,
                'metadata': lesson.metadata,
                'created_at': lesson.created_at.isoformat(),
                'updated_at': lesson.updated_at.isoformat()
            }
            
            result = self.client.table('lessons').insert(lesson_data).execute()
            
            if result.data:
                logger.info("Lesson created successfully", lesson_id=lesson.id)
                return lesson.id
            else:
                raise DatabaseError("Failed to create lesson")
                
        except Exception as e:
            logger.error("Error creating lesson", error=str(e), lesson_id=lesson.id)
            raise DatabaseError(f"Failed to create lesson: {str(e)}")
    
    async def get_lesson(self, lesson_id: str) -> Optional[LessonPlan]:
        """Retrieve a lesson by ID"""
        try:
            result = self.client.table('lessons').select('*').eq('id', lesson_id).execute()
            
            if result.data and len(result.data) > 0:
                lesson_data = result.data[0]
                return LessonPlan(**lesson_data)
            else:
                return None
                
        except Exception as e:
            logger.error("Error retrieving lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to retrieve lesson: {str(e)}")
    
    async def get_user_lessons(self, user_id: str, limit: int = 50) -> List[LessonPlan]:
        """Retrieve lessons for a specific user"""
        try:
            result = (
                self.client.table('lessons')
                .select('*')
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .limit(limit)
                .execute()
            )
            
            lessons = []
            if result.data:
                for lesson_data in result.data:
                    lessons.append(LessonPlan(**lesson_data))
            
            logger.info("Retrieved user lessons", user_id=user_id, count=len(lessons))
            return lessons
            
        except Exception as e:
            logger.error("Error retrieving user lessons", error=str(e), user_id=user_id)
            raise DatabaseError(f"Failed to retrieve user lessons: {str(e)}")
    
    async def update_lesson(self, lesson_id: str, updates: Dict[str, Any]) -> bool:
        """Update a lesson"""
        try:
            # Add updated timestamp
            updates['updated_at'] = lesson.updated_at.isoformat() if 'updated_at' in updates else None
            
            result = (
                self.client.table('lessons')
                .update(updates)
                .eq('id', lesson_id)
                .execute()
            )
            
            if result.data:
                logger.info("Lesson updated successfully", lesson_id=lesson_id)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Error updating lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to update lesson: {str(e)}")
    
    async def delete_lesson(self, lesson_id: str, user_id: str) -> bool:
        """Delete a lesson (with user ownership check)"""
        try:
            result = (
                self.client.table('lessons')
                .delete()
                .eq('id', lesson_id)
                .eq('user_id', user_id)  # Ensure user owns the lesson
                .execute()
            )
            
            if result.data:
                logger.info("Lesson deleted successfully", lesson_id=lesson_id)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Error deleting lesson", error=str(e), lesson_id=lesson_id)
            raise DatabaseError(f"Failed to delete lesson: {str(e)}")