from typing import Dict, Any, List
from app.models.lesson import SkillSpec, GenerationContext
from app.core.skills.enhanced_metadata import enhanced_skill_metadata
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedPromptBuilder:
    """Enhanced prompt builder that utilizes full framework metadata and block definitions"""
    
    def __init__(self):
        self.metadata = enhanced_skill_metadata
    
    
    def build_block_prompt(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        rag_context: str = None
    ) -> str:
        """
        Build comprehensive prompt using enhanced framework structure with cognitive complexity levels
        
        Args:
            skill: The thinking skill to use
            context: Generation context with lesson parameters
            rag_context: Optional RAG-retrieved curriculum context
            
        Returns:
            Complete, framework-informed prompt
        """
        try:
            # Get enhanced skill metadata
            skill_data = self.metadata.get_skill_with_framework_guidance(skill.name)
            if not skill_data:
                raise ValidationError(f"No enhanced metadata found for skill: {skill.name}")
            
            # Get block type definition
            block_definition = self.metadata.get_block_definition(skill.block_type)
            if not block_definition:
                raise ValidationError(f"No block definition found for: {skill.block_type}")
            
            # Get cognitive complexity level based on difficulty
            complexity_level = self.metadata.map_difficulty_to_level(context.difficulty)
            complexity_display_name = self.metadata.get_cognitive_level_display_name(complexity_level)
            
            # Get complexity-specific guidance
            complexity_guidance = self.metadata.get_cognitive_complexity_guidance(skill.name, complexity_level)
            
            # Build comprehensive prompt
            prompt_parts = [
                f"Create a {skill.block_type} activity for {context.grade} students learning about '{context.topic}' in {context.subject}.",
                "",
                "=" * 60,
                "STRUCTURAL LEARNING FRAMEWORK GUIDANCE",
                "=" * 60,
                "",
                f"BLOCK TYPE: {skill.block_type}",
                f"Definition: {block_definition['definition']}",
                f"Purpose: {block_definition['purpose']}",
                f"Methodology: {block_definition['methodology']}",
                "",
                f"KEY PRINCIPLES for {skill.block_type}:",
            ]
            
            # Add block-specific principles
            for principle in block_definition.get('key_principles', []):
                prompt_parts.append(f"• {principle}")
            
            prompt_parts.extend(["", "-" * 40, f"THINKING SKILL: {skill.name}", "-" * 40, ""])
            
            # Add skill information
            framework_guidance = skill_data.get('framework_guidance', {})
            prompt_parts.extend([
                f"Skill Purpose: {skill_data['description']}",
                f"Cognitive Purpose: {skill_data.get('cognitive_purpose', '')}",
                f"Key Principle: {framework_guidance.get('key_principle', '')}",
                ""
            ])
            
            # Add COGNITIVE COMPLEXITY LEVEL section - NEW
            prompt_parts.extend([
                "-" * 40,
                f"COGNITIVE COMPLEXITY LEVEL: {complexity_display_name}",
                "-" * 40,
                ""
            ])
            
            # Add complexity-specific guidance if available
            if complexity_guidance:
                prompt_parts.extend([
                    f"Description: {complexity_guidance.get('description', '')}",
                    f"Example: {complexity_guidance.get('example', '')}",
                    f"Question Stem: {complexity_guidance.get('question_stem', '')}",
                    f"Scaffold Level: {complexity_guidance.get('scaffold_level', '')}",
                    ""
                ])
            
            # [Rest of the method remains the same...]
            
            # Add block-specific guidance
            if skill.block_type == "MapIt":
                organizer_info = self.metadata.get_graphic_organizer_for_skill(skill.name, skill.block_type)
                if organizer_info:
                    prompt_parts.extend([
                        f"RECOMMENDED GRAPHIC ORGANIZER: {organizer_info['name']}",
                        f"Use Case: {organizer_info['use_case']}",
                        f"Description: {organizer_info['description']}",
                        ""
                    ])
            
            elif skill.block_type == "SayIt":
                # Add talk format guidance
                block_formats = block_definition.get('talk_formats', {})
                if block_formats:
                    prompt_parts.extend([
                        "TALK FORMAT OPTIONS:",
                    ])
                    for format_name, format_info in block_formats.items():
                        prompt_parts.append(f"• {format_name}: {format_info.get('description', '')}")
                    prompt_parts.append("")
                
                # Add sentence starters
                sentence_starters = self.metadata.get_sentence_starters_for_skill(skill.name, skill.block_type)
                if sentence_starters:
                    prompt_parts.extend([
                        f"SENTENCE STARTERS for {skill.name}:",
                    ])
                    for starter in sentence_starters:
                        prompt_parts.append(f"• \"{starter}\"")
                    prompt_parts.append("")
            
            elif skill.block_type == "BuildIt":
                construction_types = block_definition.get('construction_types', {})
                if construction_types:
                    prompt_parts.extend([
                        "CONSTRUCTION APPROACHES:",
                    ])
                    for const_type, const_info in construction_types.items():
                        prompt_parts.append(f"• {const_type}: {const_info.get('use_case', '')}")
                    prompt_parts.append("")
            
            # Add subject-specific guidance
            subject_guidance = self.metadata.get_subject_specific_guidance(skill.name, context.subject)
            if subject_guidance:
                prompt_parts.extend([
                    f"SUBJECT-SPECIFIC GUIDANCE for {context.subject}:",
                    f"Examples: {', '.join(subject_guidance.get('examples', []))}",
                    f"Key Vocabulary: {', '.join(subject_guidance.get('key_vocabulary', []))}",
                    f"Assessment Focus: {subject_guidance.get('assessment_focus', '')}",
                    ""
                ])
            
            # Add curriculum context
            if rag_context:
                prompt_parts.extend([
                    "CURRICULUM CONTEXT:",
                    rag_context,
                    ""
                ])
            
            # Add teacher implementation guidance
            teacher_instructions = framework_guidance.get('teacher_instructions', [])
            if teacher_instructions:
                prompt_parts.extend([
                    "TEACHER IMPLEMENTATION GUIDANCE:",
                ])
                for instruction in teacher_instructions:
                    prompt_parts.append(f"• {instruction}")
                prompt_parts.append("")
            
            # Add implementation guidance from block definition
            block_guidance = block_definition.get('implementation_guidance', [])
            if block_guidance:
                prompt_parts.extend([
                    f"{skill.block_type} IMPLEMENTATION GUIDANCE:",
                ])
                for guidance in block_guidance:
                    prompt_parts.append(f"• {guidance}")
                prompt_parts.append("")
            
            # Add common mistakes to avoid
            common_mistakes = framework_guidance.get('common_mistakes', [])
            if common_mistakes:
                prompt_parts.extend([
                    "COMMON MISTAKES TO AVOID:",
                ])
                for mistake in common_mistakes:
                    prompt_parts.append(f"• {mistake}")
                prompt_parts.append("")
            
            # Add output requirements
            prompt_parts.extend([
                "=" * 60,
                "OUTPUT REQUIREMENTS",
                "=" * 60,
                "",
                f"Create a {complexity_display_name} level activity using the {skill.name} thinking skill.",
                "",
                "Return a JSON object with the following structure:",
                "{",
                '  "title": "Engaging, age-appropriate activity title",',
                '  "description": "Clear 2-3 sentence explanation of what students will do",',
                '  "steps": ["Step 1: Specific action", "Step 2: Specific action", "Step 3: etc."],',
                f'  "supporting_question": "A question that specifically develops {skill.name} thinking at {complexity_display_name} level",',
                f'  "complexity_level": "{complexity_level}"'
            ])
            
            # Add block-specific output requirements
            if skill.block_type == "SayIt":
                prompt_parts.extend([
                    ',',
                    '  "sentence_starters": ["Starter 1", "Starter 2", "Starter 3"]'
                ])
            elif skill.block_type == "BuildIt":
                prompt_parts.extend([
                    ',',
                    '  "materials": ["Simple material 1", "Simple material 2", "etc."]'
                ])
            
            prompt_parts.extend([
                "}",
                "",
                "QUALITY REQUIREMENTS:",
                f"• Ensure the activity truly develops the {skill.name} thinking skill at the {complexity_display_name} level",
                f"• Use {skill.block_type} methodology appropriately",
                f"• Make it age-appropriate for {context.grade}",
                f"• Align with {context.curriculum} standards",
                f"• Include specific, actionable steps",
                f"• Create meaningful learning, not just busy work",
                "",
                f"Focus on creating a {complexity_display_name} level activity that genuinely helps students practice and develop {skill.name} thinking through {skill.block_type} methodology."
            ])
            
            complete_prompt = "\n".join(prompt_parts)
            
            logger.info(
                "Enhanced prompt built successfully",
                skill=skill.name,
                block_type=skill.block_type,
                complexity_level=complexity_display_name,
                prompt_length=len(complete_prompt)
            )
            
            return complete_prompt
            
        except Exception as e:
            logger.error("Error building enhanced prompt", error=str(e), skill=skill.name)
            raise ValidationError(f"Failed to build enhanced prompt: {str(e)}")
        
        def _get_difficulty_text(self, difficulty: float) -> str:
            """Convert difficulty number to descriptive text"""
            level = self.metadata.map_difficulty_to_level(difficulty)
            level_descriptions = {
                "foundational": "simple and accessible",
                "developing": "moderate complexity with some challenge",
                "proficient": "appropriately challenging",
                "advanced": "complex and sophisticated"
            }
            return level_descriptions.get(level, "moderate")


# Global instance
enhanced_prompt_builder = EnhancedPromptBuilder()