from typing import List, Optional
import uuid
from datetime import datetime
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, LessonMetadata
from app.models.lesson import LessonPlan, GenerationContext
from app.core.skills.selector import skill_selector
from app.core.generation.block_generator import block_generator
from app.core.rag.context_builder import rag_context_builder
from app.services.storage_service import storage_service
from app.utils.exceptions import SkillSelectionError, LLMGenerationError
from app.utils.logging import get_logger
import random
import time
logger = get_logger(__name__)


class LessonService:
    """Main service for lesson generation and management"""
    
    def __init__(self):
        self.skill_selector = skill_selector
        self.block_generator = block_generator
        self.rag_builder = rag_context_builder
        self.storage_service = storage_service
    
    async def generate_lesson(
        self, 
        request: LessonRequest, 
        user_id: Optional[str] = None
    ) -> LessonResponse:
        """
        Generate a complete lesson plan
        
        Args:
            request: Lesson generation request
            user_id: Optional user ID for saving the lesson
            
        Returns:
            Complete lesson response with generated blocks
        """
        try:
            # lesson_id = f"lesson-{str(uuid.uuid4())}"
            lesson_id = str(int(time.time() * 1000))  # Timestamp-based numeric ID
            
            logger.info(
                "Starting lesson generation",
                lesson_id=lesson_id,
                topic=request.topic,
                grade=request.grade,
                subject=request.subject
            )
            
            preferred_scaffolds = request.preferred_blocks
            # If no preferences provided, generate a varied sequence
            if not preferred_scaffolds:
                preferred_scaffolds = self._generate_varied_scaffold_sequence(
                    step_count=request.step_count,
                    difficulty=request.difficulty
                )
                logger.info(f"Auto-generated scaffold sequence: {preferred_scaffolds}")
            else:
                logger.info(f"Using teacher-specified scaffolds: {preferred_scaffolds}")
        
            # Step 2: Select appropriate thinking skills
            selected_skills = self.skill_selector.select_skills_for_lesson(
                difficulty=request.difficulty,
                step_count=request.step_count,
                preferred_blocks=request.preferred_blocks,
                subject=request.subject
            )
            
            # Step 3: Build generation context with RAG
            generation_context = await self.rag_builder.build_lesson_context(
                topic=request.topic,
                subject=request.subject,
                grade=request.grade,
                curriculum=request.curriculum,
                skills=selected_skills
            )
            generation_context.difficulty = request.difficulty
            
            # Step 4: Generate lesson blocks
            lesson_blocks = await self.block_generator.generate_multiple_blocks(
                skills=selected_skills,
                context=generation_context
            )
            
            # Step 5: Create lesson metadata
            lesson_metadata = self._create_lesson_metadata(
                skills=selected_skills,
                difficulty=request.difficulty,
                step_count=request.step_count
            )
            
            # Step 6: Save lesson if user provided
            if user_id:
                await self._save_lesson_plan(
                    lesson_id=lesson_id,
                    request=request,
                    blocks=lesson_blocks,
                    metadata=lesson_metadata,
                    user_id=user_id
                )
            
            # Step 7: Create response
            lesson_response = LessonResponse(
                lesson_id=lesson_id,
                topic=request.topic,
                grade=request.grade,
                subject=request.subject,
                curriculum=request.curriculum,
                difficulty=request.difficulty,
                blocks=lesson_blocks,
                metadata=lesson_metadata
            )
            
            logger.info(
                "Lesson generation completed successfully",
                lesson_id=lesson_id,
                blocks_generated=len(lesson_blocks),
                skills_used=[skill.name for skill in selected_skills]
            )
            
            return lesson_response
            
        except SkillSelectionError as e:
            logger.error("Skill selection failed", error=str(e))
            raise
        except LLMGenerationError as e:
            logger.error("Content generation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in lesson generation", error=str(e))
            raise
        
    def _generate_varied_scaffold_sequence(self, step_count: int, difficulty: float) -> List[str]:
        """Generate a varied sequence of scaffold types"""
        scaffolds = []
        
        # Always start with MapIt for organization
        if step_count >= 1:
            scaffolds.append("MapIt")
        
        # Add SayIt for explanation/discussion
        if step_count >= 2:
            scaffolds.append("SayIt")
        
        # For higher difficulty lessons with 3+ steps, add BuildIt
        if step_count >= 3 and difficulty > 0.5:
            scaffolds.append("BuildIt")
        elif step_count >= 3:
            # For easier lessons, alternate between MapIt and SayIt
            scaffolds.append("MapIt" if scaffolds[-1] == "SayIt" else "SayIt")
        
        # Fill remaining steps with variety (avoid repetition)
        while len(scaffolds) < step_count:
            # Avoid three consecutive instances of the same type
            if len(scaffolds) >= 2 and scaffolds[-1] == scaffolds[-2]:
                options = [t for t in ["MapIt", "SayIt", "BuildIt"] if t != scaffolds[-1]]
                scaffolds.append(random.choice(options))
            else:
                # Weighted selection - BuildIt less common for easier lessons
                if difficulty < 0.4:
                    weights = {"MapIt": 0.5, "SayIt": 0.4, "BuildIt": 0.1}
                elif difficulty < 0.7:
                    weights = {"MapIt": 0.4, "SayIt": 0.4, "BuildIt": 0.2}
                else:
                    weights = {"MapIt": 0.3, "SayIt": 0.3, "BuildIt": 0.4}
                
                options = list(weights.keys())
                weights_list = [weights[opt] for opt in options]
                
                scaffolds.append(random.choices(options, weights=weights_list)[0])
        
        return scaffolds
    
    async def get_lesson(self, lesson_id: str, user_id: Optional[str] = None) -> Optional[LessonResponse]:
        """Retrieve a saved lesson by ID"""
        try:
            lesson_plan = await self.storage_service.get_lesson(lesson_id)
            
            if not lesson_plan:
                return None
            
            # Check user ownership if user_id provided
            if user_id and lesson_plan.user_id != user_id:
                logger.warning("User attempted to access lesson they don't own", 
                             lesson_id=lesson_id, user_id=user_id)
                return None
            
            # Convert to response format
            lesson_response = self._lesson_plan_to_response(lesson_plan)
            
            return lesson_response
            
        except Exception as e:
            logger.error("Error retrieving lesson", error=str(e), lesson_id=lesson_id)
            raise
    
    async def get_user_lessons(self, user_id: str, limit: int = 50) -> List[LessonResponse]:
        """Get all lessons for a user"""
        try:
            lesson_plans = await self.storage_service.get_user_lessons(user_id, limit)
            
            # Convert to response format
            lesson_responses = []
            for plan in lesson_plans:
                response = self._lesson_plan_to_response(plan)
                lesson_responses.append(response)
            
            return lesson_responses
            
        except Exception as e:
            logger.error("Error retrieving user lessons", error=str(e), user_id=user_id)
            raise
    
    def _create_lesson_metadata(
        self, 
        skills: List, 
        difficulty: float, 
        step_count: int
    ) -> LessonMetadata:
        """Create metadata for the lesson"""
        
        skills_used = [skill.name for skill in skills]
        cognitive_progression = [skill.color for skill in skills]
        
        # Estimate duration based on step count and difficulty
        base_duration = step_count * 12  # 12 minutes per block
        difficulty_multiplier = 1 + (difficulty * 0.5)  # Up to 50% longer for harder lessons
        estimated_minutes = int(base_duration * difficulty_multiplier)
        
        difficulty_labels = {
            (0.0, 0.3): "Foundational",
            (0.3, 0.5): "Developing", 
            (0.5, 0.7): "Proficient",
            (0.7, 1.0): "Advanced"
        }
        
        difficulty_level = "Developing"  # default
        for (low, high), label in difficulty_labels.items():
            if low <= difficulty <= high:
                difficulty_level = label
                break
        
        return LessonMetadata(
            skills_used=skills_used,
            cognitive_progression=cognitive_progression,
            estimated_duration=f"{estimated_minutes} minutes",
            difficulty_level=difficulty_level
        )
    
    async def _save_lesson_plan(
        self,
        lesson_id: str,
        request: LessonRequest,
        blocks: List,
        metadata: LessonMetadata,
        user_id: str
    ):
        """Save the lesson plan to storage"""
        
        # Create lesson plan object
        lesson_plan = LessonPlan(
            id=lesson_id,
            user_id=user_id,
            title=f"{request.topic} - {request.grade} {request.subject}",
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            curriculum=request.curriculum,
            difficulty=request.difficulty,
            blocks=[block.dict() for block in blocks],  # Convert to dict for JSON storage
            metadata=metadata.dict()
        )
        
        # Save to storage
        await self.storage_service.save_lesson(lesson_plan)
    
    def _lesson_plan_to_response(self, lesson_plan: LessonPlan) -> LessonResponse:
        """Convert LessonPlan to LessonResponse"""
        
        # Convert blocks back from dict format
        from app.models.responses import LessonBlock
        blocks = [LessonBlock(**block_data) for block_data in lesson_plan.blocks]
        
        # Convert metadata
        metadata = LessonMetadata(**lesson_plan.metadata)
        
        return LessonResponse(
            lesson_id=lesson_plan.id,
            topic=lesson_plan.topic,
            grade=lesson_plan.grade,
            subject=lesson_plan.subject,
            curriculum=lesson_plan.curriculum,
            difficulty=lesson_plan.difficulty,
            blocks=blocks,
            metadata=metadata,
            generated_at=lesson_plan.created_at
        )


# Global instance
lesson_service = LessonService()