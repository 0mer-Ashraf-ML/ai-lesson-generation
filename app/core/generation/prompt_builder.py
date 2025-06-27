import json
from typing import Dict, Any
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader
from app.models.lesson import SkillSpec, GenerationContext
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    """Builds contextualized prompts for LLM generation"""
    
    def __init__(self, templates_path: str = None):
        if templates_path is None:
            templates_path = Path(__file__).parent.parent.parent.parent / "data" / "prompts"
        
        self.templates_path = Path(templates_path)
        self._templates_data = None
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_path.parent))
        )
        self._load_templates()
    
    def _load_templates(self):
        """Load prompt templates from JSON file"""
        try:
            templates_file = self.templates_path / "base_templates.json"
            with open(templates_file, 'r') as f:
                self._templates_data = json.load(f)
            logger.info("Prompt templates loaded successfully")
        except Exception as e:
            logger.error("Failed to load prompt templates", error=str(e))
            raise ValidationError(f"Failed to load prompt templates: {str(e)}")
    
    def build_block_prompt(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        rag_context: str = None
    ) -> str:
        """
        Build a complete prompt for generating a lesson block
        
        Args:
            skill: The thinking skill for this block
            context: Generation context with lesson parameters
            rag_context: Optional RAG-retrieved context
            
        Returns:
            Complete prompt string ready for LLM
        """
        try:
            # Get the appropriate template
            template_text = self._get_template(skill.block_type, skill.name)
            
            # Create Jinja template
            template = Template(template_text)
            
            # Prepare template variables
            template_vars = {
                'grade': context.grade,
                'subject': context.subject,
                'topic': context.topic,
                'curriculum': context.curriculum,
                'skill_name': skill.name,
                'skill_description': skill.description,
                'skill_color': skill.color,
                'block_type': skill.block_type,
                'example_question': skill.example_question,
                'curriculum_context': rag_context or context.curriculum_context or "No specific curriculum context available.",
                'difficulty_text': self._get_difficulty_text(context.difficulty)
            }
            
            # Add block-specific variables
            if skill.media_suggestion:
                template_vars['media_suggestion'] = skill.media_suggestion
            
            # Render the prompt
            prompt = template.render(**template_vars)
            
            # Add JSON schema instruction
            schema_instruction = self._get_schema_instruction(skill.block_type)
            complete_prompt = f"{prompt}\n\n{schema_instruction}"
            
            logger.debug(
                "Prompt built successfully",
                skill=skill.name,
                block_type=skill.block_type,
                prompt_length=len(complete_prompt)
            )
            
            return complete_prompt
            
        except Exception as e:
            logger.error("Error building prompt", error=str(e), skill=skill.name)
            raise ValidationError(f"Failed to build prompt: {str(e)}")
    
    def _get_template(self, block_type: str, skill_name: str) -> str:
        """Get the appropriate template for block type and skill"""
        try:
            # Try to get specific skill template first
            if (block_type in self._templates_data and 
                skill_name in self._templates_data[block_type]):
                return self._templates_data[block_type][skill_name]['template']
            
            # Fall back to generic template for block type
            generic_templates = {
                'MapIt': """Create a MapIt activity for {{grade}} students learning about {{topic}} in {{subject}}.

Use the thinking skill '{{skill_name}}' - {{skill_description}}.

Curriculum Context:
{{curriculum_context}}

The activity should use a graphic organizer appropriate for {{skill_name}}.

Return a JSON response with:
- title: A clear, engaging title for the activity
- description: 2-3 sentences explaining what students will do
- steps: An array of 3-4 clear, actionable steps
- supporting_question: A question that helps guide student thinking

Make it age-appropriate for {{grade}} level and aligned with {{curriculum}} standards.""",

                'SayIt': """Create a SayIt activity for {{grade}} students learning about {{topic}} in {{subject}}.

Use the thinking skill '{{skill_name}}' - {{skill_description}}.

Curriculum Context:
{{curriculum_context}}

The activity should focus on discussion and verbal communication.

Return a JSON response with:
- title: A clear, engaging title for the discussion activity
- description: 2-3 sentences about the speaking/discussion task
- steps: An array of 3-4 steps that guide the discussion process
- supporting_question: An open-ended question that prompts discussion
- sentence_starters: An array of 3-4 sentence starters to help students

Make it appropriate for {{grade}} level communication skills.""",

                'BuildIt': """Create a BuildIt activity for {{grade}} students learning about {{topic}} in {{subject}}.

Use the thinking skill '{{skill_name}}' - {{skill_description}}.

Curriculum Context:
{{curriculum_context}}

The activity should be hands-on and involve creating or building something.

Return a JSON response with:
- title: A clear, engaging title for the hands-on activity
- description: 2-3 sentences about what students will build/create
- steps: An array of 4-5 practical steps for the building process
- supporting_question: A question that encourages creative thinking
- materials: An array of simple, accessible materials needed

Make it safe and appropriate for {{grade}} level capabilities."""
            }
            
            if block_type in generic_templates:
                return generic_templates[block_type]
            else:
                raise ValidationError(f"No template found for block type: {block_type}")
                
        except Exception as e:
            logger.error("Error getting template", error=str(e))
            raise
    
    def _get_difficulty_text(self, difficulty: float) -> str:
        """Convert difficulty number to descriptive text"""
        if difficulty <= 0.3:
            return "simple and foundational"
        elif difficulty <= 0.5:
            return "moderate complexity"
        elif difficulty <= 0.7:
            return "challenging but achievable"
        else:
            return "advanced and complex"
    
    def _get_schema_instruction(self, block_type: str) -> str:
        """Get JSON schema instruction for the block type"""
        base_schema = """
IMPORTANT: Return ONLY valid JSON in the following format:
{
  "title": "Clear, engaging activity title",
  "description": "2-3 sentences explaining the activity",
  "steps": ["Step 1...", "Step 2...", "Step 3..."],
  "supporting_question": "A question to guide student thinking"
}"""
        
        if block_type == "SayIt":
            return base_schema.replace("}", ',\n  "sentence_starters": ["I think...", "In my opinion...", "The evidence shows..."]\n}')
        elif block_type == "BuildIt":
            return base_schema.replace("}", ',\n  "materials": ["Simple material 1", "Simple material 2"]\n}')
        else:
            return base_schema
    
    def validate_prompt_output(self, output: str) -> Dict[str, Any]:
        """Validate that LLM output matches expected JSON format"""
        try:
            # Try to parse as JSON
            parsed = json.loads(output)
            
            # Check required fields
            required_fields = ['title', 'description', 'steps', 'supporting_question']
            for field in required_fields:
                if field not in parsed:
                    raise ValidationError(f"Missing required field: {field}")
            
            # Validate types
            if not isinstance(parsed['title'], str) or len(parsed['title']) < 5:
                raise ValidationError("Title must be a non-empty string")
            
            if not isinstance(parsed['steps'], list) or len(parsed['steps']) < 2:
                raise ValidationError("Steps must be a list with at least 2 items")
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON output from LLM", error=str(e))
            raise ValidationError(f"Invalid JSON output: {str(e)}")


# Global instance
prompt_builder = PromptBuilder()