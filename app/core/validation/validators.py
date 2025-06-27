import json
import jsonschema
from typing import Dict, Any, List, Optional
from pathlib import Path
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LessonBlockValidator:
    """Validates lesson blocks against JSON schema and business rules"""
    
    def __init__(self, schema_path: str = None):
        if schema_path is None:
            schema_path = Path(__file__).parent.parent.parent.parent / "data" / "schemas" / "lesson_block.json"
        
        self.schema_path = Path(schema_path)
        self._schema = None
        self._load_schema()
    
    def _load_schema(self):
        """Load JSON schema for lesson blocks"""
        try:
            with open(self.schema_path, 'r') as f:
                self._schema = json.load(f)
            logger.info("Lesson block schema loaded successfully")
        except Exception as e:
            logger.error("Failed to load lesson block schema", error=str(e))
            raise ValidationError(f"Failed to load validation schema: {str(e)}")
    
    def validate_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single lesson block
        
        Args:
            block_data: Block data to validate
            
        Returns:
            Validated and potentially cleaned block data
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # JSON Schema validation
            jsonschema.validate(instance=block_data, schema=self._schema)
            
            # Business logic validation
            self._validate_business_rules(block_data)
            
            # Clean and normalize data
            cleaned_data = self._clean_block_data(block_data)
            
            logger.debug("Block validation successful", block_id=block_data.get('id'))
            return cleaned_data
            
        except jsonschema.ValidationError as e:
            logger.error("JSON schema validation failed", error=str(e), block_data=block_data)
            raise ValidationError(f"Block validation failed: {e.message}")
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Unexpected error in block validation", error=str(e))
            raise ValidationError(f"Block validation error: {str(e)}")
    
    def _validate_business_rules(self, block_data: Dict[str, Any]):
        """Validate business logic rules beyond JSON schema"""
        
        block_type = block_data.get('type')
        skill_name = block_data.get('skill', {}).get('name')
        
        # Rule 1: Skill-to-block-type consistency
        expected_block_types = self._get_expected_block_types_for_skill(skill_name)
        if expected_block_types and block_type not in expected_block_types:
            raise ValidationError(
                f"Skill '{skill_name}' is not typically used with {block_type} blocks. "
                f"Expected: {', '.join(expected_block_types)}"
            )
        
        # Rule 2: Block-specific field requirements
        if block_type == "SayIt":
            if not block_data.get('sentence_starters'):
                logger.warning("SayIt block missing sentence_starters", block_id=block_data.get('id'))
        
        elif block_type == "BuildIt":
            if not block_data.get('materials') and not block_data.get('criteria'):
                logger.warning("BuildIt block missing materials or criteria", block_id=block_data.get('id'))
        
        # Rule 3: Steps quality check
        steps = block_data.get('steps', [])
        if len(steps) < 2:
            raise ValidationError("Block must have at least 2 steps")
        
        # Check for actionable language in steps
        action_words = ['create', 'make', 'build', 'draw', 'write', 'discuss', 'identify', 'compare', 'sort', 'list']
        actionable_steps = sum(1 for step in steps if any(word in step.lower() for word in action_words))
        
        if actionable_steps < len(steps) * 0.5:  # At least 50% should be actionable
            logger.warning("Steps may not be sufficiently actionable", block_id=block_data.get('id'))
        
        # Rule 4: Age appropriateness (basic check)
        title = block_data.get('title', '')
        description = block_data.get('description', '')
        
        # Check for overly complex words (basic heuristic)
        complex_indicators = ['synthesis', 'paradigm', 'methodology', 'theoretical', 'conceptualization']
        text_to_check = f"{title} {description}".lower()
        
        if any(indicator in text_to_check for indicator in complex_indicators):
            logger.warning("Content may be too complex for target age group", block_id=block_data.get('id'))
    
    def _get_expected_block_types_for_skill(self, skill_name: str) -> List[str]:
        """Get expected block types for a skill"""
        
        # Mapping based on Structural Learning framework
        skill_to_blocks = {
            # Green skills - typically MapIt
            "Identify": ["MapIt"],
            "Retrieve": ["MapIt", "SayIt"],
            "Eliminate": ["MapIt"],
            "Extract": ["MapIt"],
            
            # Blue skills - typically MapIt
            "Categorise": ["MapIt"],
            "Compare": ["MapIt"],
            "Rank": ["MapIt"],
            "Sequence": ["MapIt"],
            "Connect": ["MapIt"],
            
            # Yellow skills - typically SayIt
            "Explain": ["SayIt"],
            "Validate": ["SayIt"],
            "Exemplify": ["SayIt"],
            "Verify": ["SayIt"],
            "Amplify": ["SayIt"],
            
            # Orange skills - typically SayIt
            "Verbs": ["SayIt"],
            "Adverbs": ["SayIt"],
            "Adjectives": ["SayIt"],
            "Conjunctions": ["SayIt"],
            "Prepositions": ["SayIt"],
            "Target Vocabulary": ["SayIt"],
            
            # Red skills - typically BuildIt
            "Hypothesise": ["BuildIt"],
            "Judge": ["BuildIt"],
            "Combine": ["BuildIt"],
            "Imagine": ["BuildIt"],
            "Designate": ["BuildIt"],
            "Summarise": ["SayIt", "BuildIt"],  # Can be either
            "Generate Questions": ["SayIt", "BuildIt"],
            "Integrate": ["BuildIt"],
            "Generalise": ["SayIt", "BuildIt"],
            "Complete": ["BuildIt"],
            "Elaborate": ["SayIt", "BuildIt"],
            "New Perspective": ["SayIt", "BuildIt"],
            "Infer": ["SayIt", "BuildIt"]
        }
        
        return skill_to_blocks.get(skill_name, [])  # Return empty list if not found (allow any)
    
    def _clean_block_data(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize block data"""
        
        cleaned = block_data.copy()
        
        # Trim whitespace from strings
        if 'title' in cleaned:
            cleaned['title'] = cleaned['title'].strip()
        
        if 'description' in cleaned:
            cleaned['description'] = cleaned['description'].strip()
        
        if 'supporting_question' in cleaned:
            cleaned['supporting_question'] = cleaned['supporting_question'].strip()
        
        # Clean steps
        if 'steps' in cleaned:
            cleaned['steps'] = [step.strip() for step in cleaned['steps'] if step.strip()]
        
        # Clean optional arrays
        for field in ['sentence_starters', 'materials', 'target_words', 'criteria']:
            if field in cleaned and cleaned[field]:
                cleaned[field] = [item.strip() for item in cleaned[field] if item.strip()]
        
        # Ensure media URLs are valid
        if 'media' in cleaned and cleaned['media']:
            valid_media = []
            for url in cleaned['media']:
                if url.strip() and (url.startswith('http://') or url.startswith('https://')):
                    valid_media.append(url.strip())
            cleaned['media'] = valid_media
        
        return cleaned
    
    def validate_lesson_plan(self, lesson_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate an entire lesson plan (list of blocks)
        
        Args:
            lesson_blocks: List of lesson blocks to validate
            
        Returns:
            List of validated blocks
        """
        if not lesson_blocks:
            raise ValidationError("Lesson plan must contain at least one block")
        
        if len(lesson_blocks) > 6:
            raise ValidationError("Lesson plan cannot contain more than 6 blocks")
        
        validated_blocks = []
        block_ids = set()
        
        for i, block in enumerate(lesson_blocks):
            try:
                # Validate individual block
                validated_block = self.validate_block(block)
                
                # Check for duplicate IDs
                block_id = validated_block.get('id')
                if block_id in block_ids:
                    raise ValidationError(f"Duplicate block ID: {block_id}")
                block_ids.add(block_id)
                
                validated_blocks.append(validated_block)
                
            except ValidationError as e:
                logger.error(f"Block {i+1} validation failed", error=str(e))
                raise ValidationError(f"Block {i+1} validation failed: {str(e)}")
        
        # Validate lesson-level rules
        self._validate_lesson_coherence(validated_blocks)
        
        logger.info("Lesson plan validation successful", block_count=len(validated_blocks))
        return validated_blocks
    
    def _validate_lesson_coherence(self, blocks: List[Dict[str, Any]]):
        """Validate coherence across the entire lesson"""
        
        # Check cognitive progression (loose validation)
        colors = [block['skill']['color'] for block in blocks]
        color_order = {'Green': 1, 'Blue': 2, 'Yellow': 3, 'Orange': 3, 'Red': 4}
        
        # Allow some flexibility but warn if progression seems backwards
        for i in range(1, len(colors)):
            current_level = color_order.get(colors[i], 3)
            previous_level = color_order.get(colors[i-1], 3)
            
            if current_level < previous_level - 1:  # Allow one step backward
                logger.warning(
                    "Potentially suboptimal cognitive progression",
                    progression=[f"{colors[j]}({color_order.get(colors[j], 3)})" for j in range(len(colors))]
                )
                break
        
        # Check for variety in block types
        block_types = [block['type'] for block in blocks]
        unique_types = set(block_types)
        
        if len(unique_types) == 1 and len(blocks) > 2:
            logger.warning("Lesson uses only one block type", block_type=list(unique_types)[0])


class ContentQualityValidator:
    """Validates content quality and appropriateness"""
    
    @staticmethod
    def validate_age_appropriateness(content: str, grade: str) -> bool:
        """Basic validation of age-appropriate content"""
        
        # Extract numeric grade level
        grade_number = None
        if 'Year' in grade:
            try:
                grade_number = int(grade.split()[-1])
            except:
                pass
        elif 'Grade' in grade:
            try:
                grade_number = int(grade.split()[-1])
            except:
                pass
        
        if not grade_number:
            return True  # Can't validate without grade info
        
        content_lower = content.lower()
        
        # Age-inappropriate complexity indicators
        if grade_number <= 6:  # Elementary
            complex_words = [
                'synthesize', 'paradigm', 'methodology', 'theoretical', 'conceptualization',
                'epistemological', 'phenomenological', 'dialectical', 'ontological'
            ]
            if any(word in content_lower for word in complex_words):
                return False
        
        # Check sentence complexity (basic heuristic)
        sentences = content.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        max_sentence_length = {
            1: 8, 2: 10, 3: 12, 4: 15, 5: 18, 6: 20
        }.get(grade_number, 25)
        
        if avg_sentence_length > max_sentence_length * 1.5:
            return False
        
        return True
    
    @staticmethod
    def validate_curriculum_alignment(content: str, curriculum: str) -> bool:
        """Basic validation of curriculum alignment"""
        # This would be enhanced with actual curriculum standards
        # For now, just basic checks
        
        if not curriculum:
            return True
        
        curriculum_keywords = {
            'UK KS2': ['key stage', 'national curriculum', 'attainment', 'working scientifically'],
            'NGSS': ['performance expectation', 'disciplinary core', 'crosscutting concepts'],
            'IB PYP': ['inquiry', 'conceptual understanding', 'international mindedness']
        }
        
        keywords = curriculum_keywords.get(curriculum, [])
        if not keywords:
            return True  # Unknown curriculum, assume valid
        
        # Content doesn't need to contain curriculum keywords, 
        # but shouldn't contradict them
        return True
    
    @staticmethod
    def validate_skill_alignment(content: str, skill_name: str) -> bool:
        """Validate that content actually develops the specified thinking skill"""
        
        skill_indicators = {
            'Categorise': ['group', 'sort', 'classify', 'organize', 'category'],
            'Compare': ['similar', 'different', 'alike', 'contrast', 'comparison'],
            'Sequence': ['order', 'first', 'next', 'then', 'sequence', 'step'],
            'Explain': ['because', 'reason', 'why', 'explain', 'describe'],
            'Hypothesise': ['predict', 'think', 'hypothesis', 'if', 'might'],
            'Judge': ['best', 'better', 'choose', 'decide', 'evaluate'],
            'Identify': ['find', 'point', 'name', 'identify', 'recognize'],
            'Connect': ['link', 'connect', 'relate', 'relationship', 'connection']
        }
        
        indicators = skill_indicators.get(skill_name, [])
        if not indicators:
            return True  # Unknown skill, assume valid
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in indicators)


# Global validator instances
lesson_block_validator = LessonBlockValidator()
content_quality_validator = ContentQualityValidator()