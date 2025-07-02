from typing import List, Optional
import uuid
from datetime import datetime
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, LessonMetadata
from app.models.lesson import LessonPlan, GenerationContext, SkillSpec

# Import enhanced components
from app.core.skills.enhanced_selector import enhanced_skill_selector
from app.core.generation.enhanced_prompt_builder import enhanced_prompt_builder
from app.core.generation.block_generator import block_generator
from app.core.rag.context_builder import rag_context_builder
from app.services.storage_service import storage_service
import time
import random
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
    
    def verify_skill_metadata(self, skill: SkillSpec) -> SkillSpec:
        """
        Verify and correct skill metadata against the enhanced_skills_metadata file
        
        Args:
            skill: The skill to verify
            
        Returns:
            SkillSpec with corrected color and block_type if needed
        """
        try:
            # Import the enhanced metadata
            from app.core.skills.enhanced_metadata import enhanced_skill_metadata
            
            # Look up the correct color and block_type for this skill
            correct_color = None
            correct_block_type = None
            
            # Check each color category
            for color, color_data in enhanced_skill_metadata._skills_data.items():
                # Look for the skill in this color
                for skill_data in color_data.get("skills", []):
                    if skill_data["skill"] == skill.name:
                        correct_color = color
                        correct_block_type = skill_data["block_type"]
                        break
                
                if correct_color:
                    break
            
            # If we found correct metadata, check if it matches
            if correct_color and correct_block_type:
                if skill.color != correct_color or skill.block_type != correct_block_type:
                    logger.warning(
                        f"Correcting skill metadata: {skill.name} should be {correct_color}/{correct_block_type}, "
                        f"not {skill.color}/{skill.block_type}"
                    )
                    
                    # Generate the correct icon URL
                    icon_url = self._ensure_correct_icon_url(skill.name, correct_color)
                    
                    # Return a corrected SkillSpec
                    return SkillSpec(
                        name=skill.name,
                        color=correct_color,
                        block_type=correct_block_type,
                        example_question=skill.example_question,
                        description=skill.description,
                        icon_url=icon_url,
                        media_suggestion=skill.media_suggestion
                    )
            
            # If no correction needed or metadata not found, return the original
            return skill
            
        except Exception as e:
            logger.error(f"Error verifying skill metadata for {skill.name}", error=str(e))
            return skill
        
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
    
    async def generate_lesson(
        self, 
        request: LessonRequest, 
        user_id: Optional[str] = None
    ) -> LessonResponse:
        """
        Generate a complete lesson plan with metadata verification
        
        Args:
            request: Lesson generation request
            user_id: Optional user ID for saving the lesson
            
        Returns:
            Complete lesson response with generated blocks
        """
        try:
            lesson_id = str(int(time.time() * 1000))  # Timestamp-based numeric ID
            
            logger.info(
                "Starting lesson generation",
                lesson_id=lesson_id,
                topic=request.topic,
                grade=request.grade,
                subject=request.subject
            )
            
            # Generate scaffold sequence if not provided
            preferred_scaffolds = request.preferred_blocks
            if not preferred_scaffolds:
                preferred_scaffolds = self._generate_varied_scaffold_sequence(
                    step_count=request.step_count,
                    difficulty=request.difficulty
                )
                logger.info(f"Auto-generated scaffold sequence: {preferred_scaffolds}")
            else:
                logger.info(f"Using teacher-specified scaffolds: {preferred_scaffolds}")
            
            # Select skills
            selected_skills = await self.skill_selector.select_skills_for_lesson(
                difficulty=request.difficulty,
                step_count=request.step_count,
                subject=request.subject,
                topic=request.topic,
                preferred_blocks=preferred_scaffolds
            )
            
            # Verify and correct skill metadata if needed
            verified_skills = []
            for skill in selected_skills:
                # Add verification function to the skill selector if not already there
                if hasattr(self.skill_selector, 'verify_skill_metadata'):
                    verified_skill = self.skill_selector.verify_skill_metadata(skill)
                else:
                    # Import the verification function
                    from app.core.skills.enhanced_metadata import enhanced_skill_metadata
                    
                    # Look up correct metadata
                    verified_skill = skill
                    for color, color_data in enhanced_skill_metadata._skills_data.items():
                        for skill_data in color_data.get("skills", []):
                            if skill_data["skill"] == skill.name:
                                # If metadata doesn't match, create corrected skill
                                if skill.color != color or skill.block_type != skill_data["block_type"]:
                                    logger.warning(
                                        f"Correcting skill metadata: {skill.name} should be {color}/{skill_data['block_type']}, "
                                        f"not {skill.color}/{skill.block_type}"
                                    )
                                    
                                    # Generate correct icon URL
                                    icon_url = f"https://cdn.structural-learning.com/icons/{color.lower()}_{skill.name.lower().replace(' ', '_')}.svg"
                                    
                                    verified_skill = SkillSpec(
                                        name=skill.name,
                                        color=color,
                                        block_type=skill_data["block_type"],
                                        example_question=skill.example_question,
                                        description=skill.description,
                                        icon_url=icon_url,
                                        media_suggestion=skill.media_suggestion
                                    )
                                break
                        if verified_skill != skill:
                            break
                
                verified_skills.append(verified_skill)
            
            # Log the verified skills
            logger.info(
                "Skills selected for lesson",
                lesson_id=lesson_id,
                scaffold_sequence=[skill.block_type for skill in verified_skills],
                skills=verified_skills
            )
            
            # Continue with normal lesson generation using verified skills
            generation_context = await self.rag_builder.build_lesson_context(
                topic=request.topic,
                subject=request.subject,
                grade=request.grade,
                curriculum=request.curriculum,
                skills=verified_skills
            )
            generation_context.difficulty = request.difficulty
            
            # Generate blocks
            lesson_blocks = await self.block_generator.generate_multiple_blocks(
                skills=verified_skills,
                context=generation_context
            )
            
            # Create metadata
            lesson_metadata = self._create_enhanced_lesson_metadata(
                skills=verified_skills,
                difficulty=request.difficulty,
                step_count=request.step_count,
                rag_enhanced=True
            )
            
            # Save lesson if user provided
            if user_id:
                await self._save_lesson_plan(
                    lesson_id=lesson_id,
                    request=request,
                    blocks=lesson_blocks,
                    metadata=lesson_metadata,
                    user_id=user_id
                )
            
            # Create response
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
                skills_used=[skill.name for skill in verified_skills]
            )
            
            return lesson_response
        
        except Exception as e:
            logger.error("Error in lesson generation", error=str(e))
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