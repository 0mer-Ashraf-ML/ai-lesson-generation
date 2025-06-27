import uuid
from typing import Dict, Any
from app.models.lesson import SkillSpec, GenerationContext
from app.models.responses import LessonBlock, SkillMetadata
from app.core.generation.prompt_builder import prompt_builder
from app.core.generation.llm_client import llm_service
from app.core.rag.context_builder import rag_context_builder
from app.utils.exceptions import LLMGenerationError, ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BlockGenerator:
    """Generates individual lesson blocks using LLM and RAG"""
    
    def __init__(self):
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service
        self.rag_builder = rag_context_builder
    
    async def generate_block(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        sequence_order: int = 0
    ) -> LessonBlock:
        """
        Generate a complete lesson block for a given skill
        
        Args:
            skill: The thinking skill to use
            context: Generation context with lesson parameters
            sequence_order: Position in the lesson sequence
            
        Returns:
            Complete LessonBlock object
        """
        try:
            logger.info(
                "Generating lesson block",
                skill=skill.name,
                block_type=skill.block_type,
                topic=context.topic
            )
            
            # Step 1: Build RAG-enhanced context for this specific block
            rag_context = await self.rag_builder.build_block_context(skill, context)
            
            # Step 2: Build the generation prompt
            prompt = self.prompt_builder.build_block_prompt(
                skill=skill,
                context=context,
                rag_context=rag_context
            )
            
            # Step 3: Determine generation complexity
            complexity = self._determine_complexity(context.difficulty, skill.color)
            
            # Step 4: Generate content using LLM
            llm_result = await self.llm_service.generate_lesson_block(
                prompt=prompt,
                complexity=complexity
            )
            
            # Step 5: Extract and validate the generated content
            generated_content = llm_result['content']
            self._validate_generated_content(generated_content, skill.block_type)
            
            # Step 6: Build complete LessonBlock object
            lesson_block = self._build_lesson_block(
                generated_content=generated_content,
                skill=skill,
                llm_metadata=llm_result
            )
            
            logger.info(
                "Block generated successfully",
                block_id=lesson_block.id,
                skill=skill.name,
                tokens_used=llm_result.get('usage', {}).get('total_tokens', 0)
            )
            
            return lesson_block
            
        except Exception as e:
            logger.error(
                "Error generating lesson block",
                error=str(e),
                skill=skill.name,
                topic=context.topic
            )
            raise LLMGenerationError(f"Failed to generate block for {skill.name}: {str(e)}")
    
    def _determine_complexity(self, difficulty: float, skill_color: str) -> str:
        """Determine generation complexity based on difficulty and skill color"""
        # Red skills (higher-order thinking) may need advanced model
        if skill_color == "Red" and difficulty > 0.7:
            return "advanced"
        elif difficulty <= 0.3:
            return "simple"
        else:
            return "standard"
    
    def _validate_generated_content(self, content: Dict[str, Any], block_type: str):
        """Validate that generated content meets requirements"""
        required_fields = ['title', 'description', 'steps', 'supporting_question']
        
        for field in required_fields:
            if field not in content:
                raise ValidationError(f"Generated content missing required field: {field}")
        
        # Validate field types and content
        if not isinstance(content['title'], str) or len(content['title'].strip()) < 5:
            raise ValidationError("Title must be a non-empty string with at least 5 characters")
        
        if not isinstance(content['description'], str) or len(content['description'].strip()) < 20:
            raise ValidationError("Description must be at least 20 characters long")
        
        if not isinstance(content['steps'], list) or len(content['steps']) < 2:
            raise ValidationError("Steps must be a list with at least 2 items")
        
        if not isinstance(content['supporting_question'], str) or len(content['supporting_question'].strip()) < 10:
            raise ValidationError("Supporting question must be at least 10 characters long")
        
        # Block-specific validations
        if block_type == "SayIt" and 'sentence_starters' in content:
            if not isinstance(content['sentence_starters'], list):
                raise ValidationError("Sentence starters must be a list")
        
        if block_type == "BuildIt" and 'materials' in content:
            if not isinstance(content['materials'], list):
                raise ValidationError("Materials must be a list")
    
    def _build_lesson_block(
        self,
        generated_content: Dict[str, Any],
        skill: SkillSpec,
        llm_metadata: Dict[str, Any]
    ) -> LessonBlock:
        """Build a complete LessonBlock object from generated content"""
        
        # Create skill metadata
        skill_metadata = SkillMetadata(
            name=skill.name,
            color=skill.color,
            icon_url=skill.icon_url,
            category=self._get_category_name(skill.color)
        )
        
        # Create block ID
        block_id = f"block-{str(uuid.uuid4())[:8]}"
        
        # Build media URLs if media suggestion exists
        media = []
        if skill.media_suggestion:
            media.append(f"https://cdn.structural-learning.com/templates/{skill.media_suggestion}")
        
        # Create the lesson block
        lesson_block = LessonBlock(
            id=block_id,
            type=skill.block_type,
            title=generated_content['title'].strip(),
            description=generated_content['description'].strip(),
            steps=[step.strip() for step in generated_content['steps']],
            skill=skill_metadata,
            supporting_question=generated_content['supporting_question'].strip(),
            media=media
        )
        
        # Add optional fields based on block type
        if 'sentence_starters' in generated_content:
            lesson_block.sentence_starters = generated_content['sentence_starters']
        
        if 'materials' in generated_content:
            lesson_block.materials = generated_content['materials']
        
        if 'target_words' in generated_content:
            lesson_block.target_words = generated_content['target_words']
        
        if 'criteria' in generated_content:
            lesson_block.criteria = generated_content['criteria']
        
        return lesson_block
    
    def _get_category_name(self, color: str) -> str:
        """Get human-readable category name for color"""
        color_categories = {
            "Green": "Getting Started",
            "Blue": "Organizing Ideas",
            "Yellow": "Critical Thinking",
            "Orange": "Communicating Understanding",
            "Red": "Applying Knowledge"
        }
        return color_categories.get(color, color)
    
    async def generate_multiple_blocks(
        self,
        skills: list[SkillSpec],
        context: GenerationContext
    ) -> list[LessonBlock]:
        """Generate multiple blocks for a complete lesson"""
        blocks = []
        
        for i, skill in enumerate(skills):
            try:
                block = await self.generate_block(skill, context, sequence_order=i)
                blocks.append(block)
            except Exception as e:
                logger.error(
                    "Failed to generate block in sequence",
                    skill=skill.name,
                    sequence_order=i,
                    error=str(e)
                )
                # Could implement fallback logic here
                raise
        
        return blocks


# Global instance
block_generator = BlockGenerator()