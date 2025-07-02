import uuid
from typing import Dict, Any
from app.models.lesson import SkillSpec, GenerationContext
from app.models.responses import LessonBlock, SkillMetadata
from app.core.generation.prompt_builder import prompt_builder
from app.core.generation.llm_client import llm_service
from app.core.rag.context_builder import rag_context_builder
from app.utils.exceptions import LLMGenerationError, ValidationError
from app.utils.logging import get_logger
from app.core.rag.scaffold_retriever import scaffold_retriever

logger = get_logger(__name__)


class BlockGenerator:
    """Generates individual lesson blocks using LLM and RAG"""
    
    def __init__(self):
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service
        self.rag_builder = rag_context_builder
    
    
    def _verify_skill_metadata(self, skill: SkillSpec) -> SkillSpec:
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
                    icon_url = f"https://cdn.structural-learning.com/icons/{correct_color.lower()}_{skill.name.lower().replace(' ', '_')}.svg"
                    
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
        
    async def generate_block(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        sequence_order: int = 0
    ) -> LessonBlock:
        """
        Generate a complete lesson block for a given skill, preserving color and block type
        
        Args:
            skill: The thinking skill to use
            context: Generation context with lesson parameters
            sequence_order: Position in the lesson sequence
            
        Returns:
                Complete LessonBlock object with resources
        """
        try:
            # First, verify the skill has the correct color and block type from metadata
            verified_skill = self._verify_skill_metadata(skill)
            
            logger.info(
                "Generating lesson block",
                skill=verified_skill.name,
                color=verified_skill.color,  # Log the color
                block_type=verified_skill.block_type,
                topic=context.topic
            )
            
            # Retrieve scaffold resources
            scaffold_resources = await scaffold_retriever.retrieve_scaffold_resources(
                scaffold_type=verified_skill.block_type,
                skill_name=verified_skill.name,
                topic=context.topic,
                top_k=2
            )
            
            # Build RAG-enhanced context
            rag_context = await self.rag_builder.build_block_context(verified_skill, context)
            
            # Add resource hints to context
            if scaffold_resources["pdfs"]:
                resource_hints = "\n\nAvailable resources for this activity:\n"
                for pdf in scaffold_resources["pdfs"]:
                    resource_hints += f"- {pdf['name']}: {pdf['content_preview'][:100]}...\n"
                rag_context += resource_hints
            
            # Build the generation prompt
            prompt = self.prompt_builder.build_block_prompt(
                skill=verified_skill,
                context=context,
                rag_context=rag_context
            )
            
            # Determine generation complexity
            complexity = self._determine_complexity(context.difficulty, verified_skill.color)
            
            # Generate content using LLM
            llm_result = await self.llm_service.generate_lesson_block(
                prompt=prompt,
                complexity=complexity
            )
            
            # Extract and validate the generated content
            generated_content = llm_result['content']
            self._validate_generated_content(generated_content, verified_skill.block_type)
            
            # Build complete LessonBlock object with resources
            lesson_block = self._build_enhanced_lesson_block(
                generated_content=generated_content,
                skill=verified_skill,  # Use the verified skill
                llm_metadata=llm_result,
                scaffold_resources=scaffold_resources
            )
            
            logger.info(
                "Block generated successfully",
                block_id=lesson_block.id,
                skill=verified_skill.name,
                color=verified_skill.color,  # Log the color
                tokens_used=llm_result.get('usage', {}).get('total_tokens', 0),
                resources_attached=len(lesson_block.resources) if hasattr(lesson_block, "resources") else 0
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

        
    
    def _build_enhanced_lesson_block(
        self,
        generated_content: Dict[str, Any],
        skill: SkillSpec,
        llm_metadata: Dict[str, Any],
        scaffold_resources: Dict[str, Any]
    ) -> LessonBlock:
        """Build a complete LessonBlock object with scaffold resources and complexity level"""
        
        # Create skill metadata
        skill_metadata = SkillMetadata(
            name=skill.name,
            color=skill.color,
            icon_url=skill.icon_url,
            category=self._get_category_name(skill.color)
        )
        
        # Create block ID
        block_id = f"block-{str(uuid.uuid4())[:8]}"
        
        # Build media URLs list
        media = []
        
        # Add scaffold image if available
        if scaffold_resources.get("image"):
            media.append(scaffold_resources["image"])
        # Fall back to default media suggestion
        elif skill.media_suggestion:
            media.append(f"https://cdn.structural-learning.com/templates/{skill.media_suggestion}")
        
        # Get complexity level from generated content or use default
        from app.core.skills.enhanced_metadata import enhanced_skill_metadata
        
        complexity_level = generated_content.get('complexity_level', 'thinking_harder')
        complexity_display_name = enhanced_skill_metadata.get_cognitive_level_display_name(complexity_level)
        
        # Create the lesson block
        lesson_block = LessonBlock(
            id=block_id,
            type=skill.block_type,
            title=generated_content['title'].strip(),
            description=generated_content['description'].strip(),
            steps=[step.strip() for step in generated_content['steps']],
            skill=skill_metadata,
            supporting_question=generated_content['supporting_question'].strip(),
            complexity_level=complexity_level,  # Add this field
            complexity_display_name=complexity_display_name,  # Add this field
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
        
        # Add resource links
        from app.models.responses import ResourceLink
        
        resource_links = []
        
        # Add PDF resources
        for pdf in scaffold_resources.get("pdfs", []):
            resource_links.append(ResourceLink(
                type="pdf",
                name=pdf.get("name", "Resource"),
                description=f"{skill.block_type} resource for {skill.name}",
                url=pdf.get("url", "")
            ))
        
        # Add video resource if available
        if scaffold_resources.get("video"):
            resource_links.append(ResourceLink(
                type="video",
                name=f"{skill.name} {skill.block_type} Tutorial",
                description=f"How to implement {skill.name} thinking skill",
                url=scaffold_resources.get("video")
            ))
        
        # Set resources on the block
        lesson_block.resources = resource_links
        
        return lesson_block

    
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
        
        # Validate complexity level if present
        if 'complexity_level' in content:
            valid_levels = ['getting_started', 'thinking_harder', 'stretching_thinking']
            if content['complexity_level'] not in valid_levels:
                raise ValidationError(f"Invalid complexity level: {content['complexity_level']}. Must be one of: {', '.join(valid_levels)}")
        
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