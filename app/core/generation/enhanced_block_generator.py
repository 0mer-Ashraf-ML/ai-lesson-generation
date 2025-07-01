import uuid
from typing import Dict, Any, List, Optional, Tuple
from app.models.lesson import SkillSpec, GenerationContext
from app.models.responses import LessonBlock, SkillMetadata, ResourceLink
from app.core.generation.scaffolding_assessor import scaffolding_assessor
from app.core.generation.prompt_builder import prompt_builder
from app.core.generation.llm_client import llm_service
from app.core.rag.context_builder import rag_context_builder
from app.core.rag.scaffold_retriever import scaffold_retriever
from app.utils.exceptions import LLMGenerationError, ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedBlockGenerator:
    """Enhanced block generator with intelligent scaffolding and time awareness"""
    
    def __init__(self):
        self.scaffolding_assessor = scaffolding_assessor
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service
        self.rag_builder = rag_context_builder
        self.scaffold_retriever = scaffold_retriever
    
    async def generate_adaptive_lesson_blocks(
        self,
        skills: List[SkillSpec],
        context: GenerationContext,
        available_time_minutes: Optional[int] = None,
        time_flexibility: str = "moderate"
    ) -> Tuple[List[LessonBlock], Dict[str, Any]]:
        """
        Generate blocks with intelligent scaffolding decisions
        
        Args:
            skills: List of skills for the lesson
            context: Generation context
            available_time_minutes: Total available time
            time_flexibility: How strict the time constraint is
            
        Returns:
            Tuple of (lesson_blocks, scaffolding_summary)
        """
        try:
            logger.info(
                "Starting adaptive block generation",
                skills=[skill.name for skill in skills],
                available_time=available_time_minutes,
                time_flexibility=time_flexibility
            )
            
            # Make scaffolding decisions for each skill
            scaffold_decisions = await self._plan_scaffolding_strategy(
                skills=skills,
                context=context,
                available_time_minutes=available_time_minutes,
                time_flexibility=time_flexibility
            )
            
            # Generate blocks based on decisions
            lesson_blocks = []
            total_estimated_time = 0
            
            for i, (skill, decision) in enumerate(zip(skills, scaffold_decisions)):
                if decision["use_scaffold"]:
                    # Generate full scaffold block
                    block = await self._generate_full_scaffold_block(
                        skill=skill,
                        context=context,
                        sequence_order=i,
                    )
                else:
                    # Generate simple prompt block
                    block = await self._generate_simple_prompt_block(
                        skill=skill,
                        context=context,
                        sequence_order=i,
                        prompt_data=decision["prompt_data"]
                    )
                
                lesson_blocks.append(block)
                total_estimated_time += decision["estimated_time"]
            
            # Create scaffolding summary
            scaffolding_summary = self.scaffolding_assessor.get_scaffolding_summary(
                scaffold_decisions=scaffold_decisions,
                total_time_estimate=total_estimated_time
            )
            
            logger.info(
                "Adaptive block generation completed",
                blocks_generated=len(lesson_blocks),
                full_scaffolds=scaffolding_summary["full_scaffolds"],
                simple_prompts=scaffolding_summary["simple_prompts"],
                total_time_estimate=total_estimated_time
            )
            
            return lesson_blocks, scaffolding_summary
            
        except Exception as e:
            logger.error("Error in adaptive block generation", error=str(e))
            raise LLMGenerationError(f"Failed to generate adaptive blocks: {str(e)}")
    
    async def _plan_scaffolding_strategy(
        self,
        skills: List[SkillSpec],
        context: GenerationContext,
        available_time_minutes: Optional[int] = None,
        time_flexibility: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """Plan which skills get full scaffolds vs simple prompts"""
        
        scaffold_decisions = []
        previous_scaffolds_count = 0
        
        for i, skill in enumerate(skills):
            # Assess if this skill should use full scaffolding
            use_scaffold = self.scaffolding_assessor.should_use_full_scaffold(
                skill=skill,
                context=context,
                available_time_minutes=available_time_minutes,
                sequence_position=i,
                total_steps=len(skills),
                previous_scaffolds_count=previous_scaffolds_count
            )
            
            # Generate prompt data if using simple prompt
            prompt_data = None
            if not use_scaffold:
                prompt_data = self.scaffolding_assessor.generate_simple_prompt(skill, context)
            
            # Estimate time for this activity
            estimated_time = self.scaffolding_assessor.estimate_activity_time(
                use_scaffold=use_scaffold,
                skill=skill,
                context=context
            )
            
            # Apply time flexibility adjustments
            if time_flexibility == "strict" and available_time_minutes:
                # Force more prompts if time is very tight
                remaining_skills = len(skills) - i
                remaining_time = available_time_minutes - sum(d["estimated_time"] for d in scaffold_decisions)
                avg_time_per_remaining = remaining_time / remaining_skills if remaining_skills > 0 else 0
                
                if estimated_time > avg_time_per_remaining and use_scaffold:
                    # Switch to prompt to save time
                    use_scaffold = False
                    prompt_data = self.scaffolding_assessor.generate_simple_prompt(skill, context)
                    estimated_time = self.scaffolding_assessor.estimate_activity_time(False, skill, context)
            
            decision = {
                "skill_name": skill.name,
                "skill_color": skill.color,
                "block_type": skill.block_type,
                "use_scaffold": use_scaffold,
                "estimated_time": estimated_time,
                "prompt_data": prompt_data,
                "sequence_position": i,
                "decision_factors": self._get_decision_factors(skill, use_scaffold, available_time_minutes)
            }
            
            scaffold_decisions.append(decision)
            
            # Update scaffolds count for next iteration
            if use_scaffold:
                previous_scaffolds_count += 1
        
        return scaffold_decisions
    
    def _get_decision_factors(self, skill: SkillSpec, use_scaffold: bool, available_time: Optional[int]) -> List[str]:
        """Get human-readable reasons for scaffolding decision"""
        factors = []
        
        if use_scaffold:
            if skill.block_type == "BuildIt":
                factors.append("BuildIt activities benefit from scaffolding")
            if skill.color in ["Orange", "Red"]:
                factors.append("Advanced thinking skills need structure")
            if skill.name in ["Categorise", "Sequence", "Hypothesise"]:
                factors.append("Complex skill requires guided practice")
        else:
            if available_time and available_time < 45:
                factors.append("Time constraints favor discussion")
            if skill.color == "Green":
                factors.append("Foundation skill works well with prompts")
            if skill.name in ["Identify", "Retrieve", "Explain"]:
                factors.append("Skill suitable for open discussion")
        
        return factors
    
    async def _generate_full_scaffold_block(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        sequence_order: int,
    ) -> LessonBlock:
        """Generate a full scaffold block (existing logic with enhancements)"""
        
        # Get scaffold resources
        scaffold_resources = await self.scaffold_retriever.retrieve_scaffold_resources(
            scaffold_type=skill.block_type,
            skill_name=skill.name,
            topic=context.topic,
            top_k=2
        )
        
        # Build RAG-enhanced context
        rag_context = await self.rag_builder.build_block_context(skill, context)
        
        # Add resource hints to context
        if scaffold_resources["pdfs"]:
            resource_hints = "\n\nAvailable resources for this activity:\n"
            for pdf in scaffold_resources["pdfs"]:
                resource_hints += f"- {pdf['name']}: {pdf['content_preview'][:100]}...\n"
            rag_context += resource_hints
        
        # Build generation prompt
        prompt = self.prompt_builder.build_block_prompt(
            skill=skill,
            context=context,
            rag_context=rag_context
        )
        
        # Generate content using LLM
        complexity = self._determine_complexity(context.difficulty, skill.color)
        llm_result = await self.llm_service.generate_lesson_block(
            prompt=prompt,
            complexity=complexity
        )
        
        # Validate generated content
        generated_content = llm_result['content']
        self._validate_generated_content(generated_content, skill.block_type)
        
        # Build complete lesson block
        lesson_block = self._build_enhanced_lesson_block(
            generated_content=generated_content,
            skill=skill,
            llm_metadata=llm_result,
            scaffold_resources=scaffold_resources,
            block_type="scaffold"
        )
        
        return lesson_block
    
    async def _generate_simple_prompt_block(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        sequence_order: int,
        prompt_data: Dict[str, Any]
    ) -> LessonBlock:
        """Generate a simple prompt block instead of full scaffold"""
        
        # Create skill metadata
        skill_metadata = SkillMetadata(
            name=skill.name,
            color=skill.color,
            icon_url=skill.icon_url,
            category=self._get_category_name(skill.color)
        )
        
        # Create block ID
        block_id = f"prompt-{str(uuid.uuid4())[:8]}"
        
        # Build steps for prompt activity
        steps = [
            f"Present the question: {prompt_data['main_prompt']}",
            f"Use {prompt_data['interaction_type'].replace('_', ' ')} format",
            "Give students time to think and respond"
        ]
        
        # Add follow-up steps if available
        if prompt_data.get('follow_up_questions'):
            steps.append("Ask follow-up questions to deepen thinking")
        
        steps.append("Summarize key insights from student responses")
        
        # Create the lesson block
        lesson_block = LessonBlock(
            id=block_id,
            type="Prompt",
            title=f"{skill.name}: {context.topic}",
            description=f"Quick {skill.name} thinking discussion about {context.topic}",
            steps=steps,
            skill=skill_metadata,
            supporting_question=prompt_data['main_prompt'],
            media=[],
            interaction_type=prompt_data['interaction_type'],
            follow_up_questions=prompt_data.get('follow_up_questions', []),
            success_indicators=prompt_data.get('success_indicators', []),
            estimated_duration=prompt_data['duration_minutes']
        )
        
        logger.info(
            "Generated simple prompt block",
            block_id=block_id,
            skill=skill.name,
            interaction_type=prompt_data['interaction_type']
        )
        
        return lesson_block
    
    def _build_enhanced_lesson_block(
        self,
        generated_content: Dict[str, Any],
        skill: SkillSpec,
        llm_metadata: Dict[str, Any],
        scaffold_resources: Dict[str, Any],
        block_type: str = "scaffold"
    ) -> LessonBlock:
        """Build enhanced lesson block with all resources"""
        
        # Create skill metadata
        skill_metadata = SkillMetadata(
            name=skill.name,
            color=skill.color,
            icon_url=skill.icon_url,
            category=self._get_category_name(skill.color)
        )
        
        # Create block ID
        block_id = f"block-{str(uuid.uuid4())[:8]}"
        
        # Build media URLs
        media = []
        if scaffold_resources.get("image"):
            media.append(scaffold_resources["image"])
        elif skill.media_suggestion:
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
        
        # Add resource links
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
                
        lesson_block.resources = resource_links
        
        return lesson_block
    
    def _determine_complexity(self, difficulty: float, skill_color: str) -> str:
        """Determine generation complexity"""
        if skill_color == "Red" and difficulty > 0.7:
            return "advanced"
        elif difficulty <= 0.3:
            return "simple"
        else:
            return "standard"
    
    def _validate_generated_content(self, content: Dict[str, Any], block_type: str):
        """Validate generated content"""
        required_fields = ['title', 'description', 'steps', 'supporting_question']
        
        for field in required_fields:
            if field not in content:
                raise ValidationError(f"Generated content missing required field: {field}")
        
        if not isinstance(content['title'], str) or len(content['title'].strip()) < 5:
            raise ValidationError("Title must be a non-empty string with at least 5 characters")
        
        if not isinstance(content['steps'], list) or len(content['steps']) < 2:
            raise ValidationError("Steps must be a list with at least 2 items")
    
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
    
    async def generate_single_block(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        sequence_order: int = 0,
        use_adaptive_scaffolding: bool = True
    ) -> LessonBlock:
        """Generate a single block (for backward compatibility)"""
        
        if use_adaptive_scaffolding:
            # Use adaptive logic
            blocks, _ = await self.generate_adaptive_lesson_blocks(
                skills=[skill],
                context=context
            )
            return blocks[0]
        else:
            # Use original logic
            return await self._generate_full_scaffold_block(
                skill=skill,
                context=context,
                sequence_order=sequence_order,
                skill_cards=[]
            )


# Global instance
enhanced_block_generator = EnhancedBlockGenerator()