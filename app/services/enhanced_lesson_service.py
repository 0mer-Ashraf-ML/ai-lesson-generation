from typing import List, Optional
import uuid
from datetime import datetime
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, LessonMetadata
from app.models.lesson import LessonPlan, GenerationContext

# Import enhanced components
from app.core.skills.enhanced_selector import enhanced_skill_selector
from app.core.generation.enhanced_prompt_builder import enhanced_prompt_builder
from app.core.generation.block_generator import block_generator
from app.core.rag.context_builder import rag_context_builder
from app.services.storage_service import storage_service

from app.utils.exceptions import SkillSelectionError, LLMGenerationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedLessonService:
    """Enhanced lesson service using framework-aware components"""
    
    def __init__(self):
        self.skill_selector = enhanced_skill_selector
        self.prompt_builder = enhanced_prompt_builder
        self.block_generator = block_generator
        self.rag_builder = rag_context_builder
        self.storage_service = storage_service
        
        # Update block generator to use enhanced prompt builder
        self.block_generator.prompt_builder = enhanced_prompt_builder
    
    async def generate_lesson(
        self, 
        request: LessonRequest, 
        user_id: Optional[str] = None
    ) -> LessonResponse:
        """
        Generate a complete lesson plan using enhanced framework components
        
        Args:
            request: Lesson generation request
            user_id: Optional user ID for saving the lesson
            
        Returns:
            Complete lesson response with framework-informed blocks
        """
        try:
            lesson_id = f"lesson-{str(uuid.uuid4())}"
            
            logger.info(
                "Starting enhanced lesson generation",
                lesson_id=lesson_id,
                topic=request.topic,
                grade=request.grade,
                subject=request.subject,
                difficulty=request.difficulty
            )
            
            # Step 1: Enhanced skill selection with subject awareness
            selected_skills = self.skill_selector.select_skills_for_lesson(
                difficulty=request.difficulty,
                step_count=request.step_count,
                subject=request.subject,
                topic=request.topic,
                preferred_blocks=request.preferred_blocks
            )
            
            logger.info(
                "Skills selected with enhanced logic",
                skills=[skill.name for skill in selected_skills],
                colors=[skill.color for skill in selected_skills]
            )
            
            # Step 2: Build generation context with RAG
            generation_context = await self.rag_builder.build_lesson_context(
                topic=request.topic,
                subject=request.subject,
                grade=request.grade,
                curriculum=request.curriculum,
                skills=selected_skills
            )
            generation_context.difficulty = request.difficulty
            
            # Step 3: Generate lesson blocks using enhanced framework guidance
            lesson_blocks = await self._generate_enhanced_blocks(
                skills=selected_skills,
                context=generation_context
            )
            
            # Step 4: Create enhanced lesson metadata
            lesson_metadata = self._create_enhanced_lesson_metadata(
                skills=selected_skills,
                difficulty=request.difficulty,
                step_count=request.step_count,
                subject=request.subject
            )
            
            # Step 5: Save lesson if user provided
            if user_id:
                await self._save_lesson_plan(
                    lesson_id=lesson_id,
                    request=request,
                    blocks=lesson_blocks,
                    metadata=lesson_metadata,
                    user_id=user_id
                )
            
            # Step 6: Create response
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
                "Enhanced lesson generation completed successfully",
                lesson_id=lesson_id,
                blocks_generated=len(lesson_blocks),
                skills_used=[skill.name for skill in selected_skills],
                framework_enhanced=True
            )
            
            return lesson_response
            
        except SkillSelectionError as e:
            logger.error("Enhanced skill selection failed", error=str(e))
            raise
        except LLMGenerationError as e:
            logger.error("Enhanced content generation failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in enhanced lesson generation", error=str(e))
            raise
    
    async def _generate_enhanced_blocks(
        self,
        skills: List,
        context: GenerationContext
    ) -> List:
        """Generate blocks using enhanced framework-aware components"""
        
        blocks = []
        
        for i, skill in enumerate(skills):
            try:
                logger.info(
                    "Generating enhanced block",
                    skill=skill.name,
                    block_type=skill.block_type,
                    position=i+1,
                    total_blocks=len(skills)
                )
                
                # Generate block with enhanced framework guidance
                block = await self.block_generator.generate_block(
                    skill=skill,
                    context=context,
                    sequence_order=i
                )
                
                blocks.append(block)
                
                logger.info(
                    "Enhanced block generated successfully",
                    block_id=block.id,
                    skill=skill.name,
                    framework_informed=True
                )
                
            except Exception as e:
                logger.error(
                    "Failed to generate enhanced block",
                    skill=skill.name,
                    sequence_order=i,
                    error=str(e)
                )
                raise
        
        return blocks
    
    def _create_enhanced_lesson_metadata(
        self, 
        skills: List, 
        difficulty: float, 
        step_count: int,
        subject: str
    ) -> LessonMetadata:
        """Create enhanced metadata with framework insights"""
        
        skills_used = [skill.name for skill in skills]
        cognitive_progression = [skill.color for skill in skills]
        
        # Enhanced duration estimation based on block types
        duration_by_block = {
            "MapIt": 15,    # Visual activities need more time
            "SayIt": 12,    # Discussion activities  
            "BuildIt": 20   # Construction activities need most time
        }
        
        total_minutes = sum(duration_by_block.get(skill.block_type, 12) for skill in skills)
        
        # Adjust for difficulty
        difficulty_multiplier = 1 + (difficulty * 0.3)  # Up to 30% longer for harder lessons
        estimated_minutes = int(total_minutes * difficulty_multiplier)
        
        # Enhanced difficulty labels with framework context
        difficulty_labels = {
            (0.0, 0.25): "Foundational - Building basic understanding",
            (0.25, 0.5): "Developing - Applying skills with support", 
            (0.5, 0.75): "Proficient - Independent skill application",
            (0.75, 1.0): "Advanced - Complex synthesis and evaluation"
        }
        
        difficulty_level = "Developing"  # default
        for (low, high), label in difficulty_labels.items():
            if low <= difficulty <= high:
                difficulty_level = label
                break
        
        # Add framework-specific metadata
        block_types_used = list(set(skill.block_type for skill in skills))
        cognitive_categories = list(set(skill.color for skill in skills))
        
        return LessonMetadata(
            skills_used=skills_used,
            cognitive_progression=cognitive_progression,
            estimated_duration=f"{estimated_minutes} minutes",
            difficulty_level=difficulty_level,
            # Enhanced metadata
            block_types_used=block_types_used,
            cognitive_categories=cognitive_categories,
            framework_version="Enhanced v1.0",
            subject_optimized=True
        )
    
    async def _save_lesson_plan(
        self,
        lesson_id: str,
        request: LessonRequest,
        blocks: List,
        metadata: LessonMetadata,
        user_id: str
    ):
        """Save the enhanced lesson plan to storage"""
        
        # Create lesson plan object
        lesson_plan = LessonPlan(
            id=lesson_id,
            user_id=user_id,
            title=f"{request.topic} - {request.grade} {request.subject} (Enhanced)",
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            curriculum=request.curriculum,
            difficulty=request.difficulty,
            blocks=[block.dict() for block in blocks],  # Convert to dict for JSON storage
            metadata={
                **metadata.dict(),
                "enhancement_version": "v1.0",
                "framework_utilized": True
            }
        )
        
        # Save to storage
        await self.storage_service.save_lesson(lesson_plan)
    
    # Inherit other methods from base service
    async def get_lesson(self, lesson_id: str, user_id: Optional[str] = None):
        """Get lesson - reuse from storage service"""
        return await self.storage_service.get_lesson(lesson_id)
    
    async def get_user_lessons(self, user_id: str, limit: int = 50):
        """Get user lessons - reuse from storage service"""
        return await self.storage_service.get_user_lessons(user_id, limit)


# Global instance
enhanced_lesson_service = EnhancedLessonService()