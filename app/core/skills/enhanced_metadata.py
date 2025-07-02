import json
from typing import Dict, List, Optional
from pathlib import Path
from app.models.lesson import SkillSpec
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedSkillMetadataManager:
    """Enhanced skill metadata manager with framework guidance"""
    
    def __init__(self, skills_file_path: str = None, blocks_file_path: str = None):
        if skills_file_path is None:
            skills_file_path = Path(__file__).parent.parent.parent.parent / "data" / "skills" / "enhanced_skills_metadata.json"
        if blocks_file_path is None:
            blocks_file_path = Path(__file__).parent.parent.parent.parent / "data" / "blocks" / "block_definitions.json"
        
        self.skills_file_path = Path(skills_file_path)
        self.blocks_file_path = Path(blocks_file_path)
        self._skills_data: Optional[Dict] = None
        self._blocks_data: Optional[Dict] = None
        self._load_data()
    
    def _load_data(self):
        """Load enhanced skills and block definitions"""
        try:
            # Load skills metadata
            with open(self.skills_file_path, 'r') as f:
                self._skills_data = json.load(f)
            
            # Load block definitions
            with open(self.blocks_file_path, 'r') as f:
                self._blocks_data = json.load(f)
            
            logger.info("Enhanced skills and block metadata loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load enhanced metadata", error=str(e))
            raise ValidationError(f"Failed to load enhanced metadata: {str(e)}")
    
    def get_skill_with_framework_guidance(self, skill_name: str) -> Optional[Dict]:
        """Get skill with full framework guidance"""
        for color, color_data in self._skills_data.items():
            for skill_data in color_data["skills"]:
                if skill_data["skill"] == skill_name:
                    return {
                        **skill_data,
                        "color": color,
                        "category": color_data["category"],
                        "cognitive_purpose": color_data["cognitive_purpose"]
                    }
        return None
    
    def get_block_definition(self, block_type: str) -> Optional[Dict]:
        """Get complete block type definition"""
        return self._blocks_data.get(block_type)
    
    def get_subject_specific_guidance(self, skill_name: str, subject: str) -> Optional[Dict]:
        """Get subject-specific guidance for a skill"""
        skill_data = self.get_skill_with_framework_guidance(skill_name)
        if skill_data and "subject_applications" in skill_data:
            return skill_data["subject_applications"].get(subject)
        return None
    
    def get_difficulty_guidance(self, skill_name: str, difficulty_level: str) -> Optional[Dict]:
        """Get difficulty-specific guidance for a skill"""
        skill_data = self.get_skill_with_framework_guidance(skill_name)
        if skill_data and "difficulty_levels" in skill_data:
            return skill_data["difficulty_levels"].get(difficulty_level)
        return None
    
    def get_graphic_organizer_for_skill(self, skill_name: str, block_type: str) -> Optional[Dict]:
        """Get appropriate graphic organizer for a skill"""
        if block_type != "MapIt":
            return None
        
        block_def = self.get_block_definition(block_type)
        if not block_def or "graphic_organizers" not in block_def:
            return None
        
        # Find organizer that matches the skill
        for org_name, org_info in block_def["graphic_organizers"].items():
            if skill_name in org_info.get("skills", []):
                return {
                    "name": org_name,
                    "use_case": org_info["use_case"],
                    "description": org_info["description"]
                }
        
        # Return first organizer as fallback
        first_org = list(block_def["graphic_organizers"].items())[0]
        return {
            "name": first_org[0],
            "use_case": first_org[1]["use_case"], 
            "description": first_org[1]["description"]
        }
    
    def get_sentence_starters_for_skill(self, skill_name: str, block_type: str) -> List[str]:
        """Get sentence starters for SayIt activities"""
        if block_type != "SayIt":
            return []
        
        # First check skill-specific scaffolds
        skill_data = self.get_skill_with_framework_guidance(skill_name)
        if skill_data and "framework_guidance" in skill_data:
            scaffolds = skill_data["framework_guidance"].get("student_scaffolds", [])
            if scaffolds:
                return scaffolds
        
        # Fallback to block-level sentence starters
        block_def = self.get_block_definition(block_type)
        if block_def and "sentence_starters" in block_def:
            return block_def["sentence_starters"].get(skill_name, [])
        
        return []
    
    def map_difficulty_to_level(self, difficulty: float) -> str:
        """Map difficulty float to cognitive complexity level name
        
        Args:
            difficulty: A float between 0.0 and 1.0 representing difficulty
            
        Returns:
            String representing the cognitive complexity level
        """
        if difficulty <= 0.33:
            return "getting_started"
        elif difficulty <= 0.67:
            return "thinking_harder"
        else:
            return "stretching_thinking"
        
    def get_cognitive_level_display_name(self, level: str) -> str:
        """Get the display name for a cognitive complexity level
        
        Args:
            level: Internal level name (getting_started, thinking_harder, stretching_thinking)
            
        Returns:
            User-friendly display name
        """
        display_names = {
            "getting_started": "Getting Started",
            "thinking_harder": "Thinking Harder",
            "stretching_thinking": "Stretching Thinking"
        }
        return display_names.get(level, level.replace("_", " ").title())
    
    def get_cognitive_complexity_guidance(self, skill_name: str, complexity_level: str) -> Optional[Dict]:
        """Get guidance for a specific cognitive complexity level of a skill
        
        Args:
            skill_name: The name of the thinking skill
            complexity_level: The cognitive complexity level (getting_started, thinking_harder, stretching_thinking)
            
        Returns:
            Dictionary containing guidance for the specified complexity level, or None if not found
        """
        skill_data = self.get_skill_with_framework_guidance(skill_name)
        if not skill_data:
            return None
            
        # Check if skill has cognitive complexity levels defined
        if "cognitive_complexity_levels" not in skill_data:
            return None
            
        # Return guidance for the specified level
        complexity_levels = skill_data["cognitive_complexity_levels"]
        return complexity_levels.get(complexity_level)
    
    def get_skills_for_subject_preference(self, subject: str) -> Dict[str, float]:
        """Get skill preferences based on subject area"""
        
        # This could be enhanced with actual data analysis
        # For now, using logical preferences
        preferences = {
            "Science": {
                "Categorise": 0.9,
                "Compare": 0.8, 
                "Hypothesise": 0.9,
                "Explain": 0.8,
                "Verify": 0.7
            },
            "Mathematics": {
                "Sequence": 0.9,
                "Compare": 0.8,
                "Categorise": 0.7,
                "Judge": 0.6
            },
            "History": {
                "Retrieve": 0.9,
                "Validate": 0.8,
                "New Perspective": 0.8,
                "Explain": 0.7
            },
            "English": {
                "Target Vocabulary": 0.9,
                "Explain": 0.8,
                "Elaborate": 0.8,
                "Judge": 0.7
            }
        }
        
        return preferences.get(subject, {})


# Global instance
enhanced_skill_metadata = EnhancedSkillMetadataManager()