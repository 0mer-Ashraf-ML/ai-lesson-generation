import json
from typing import Dict, List, Optional
from pathlib import Path
from app.models.lesson import SkillSpec
from app.utils.exceptions import ValidationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SkillMetadataManager:
    """Manages thinking skills metadata"""
    
    def __init__(self, skills_file_path: str = None):
        if skills_file_path is None:
            skills_file_path = Path(__file__).parent.parent.parent.parent / "data" / "skills" / "skills_metadata.json"
        
        self.skills_file_path = Path(skills_file_path)
        self._skills_data: Optional[Dict] = None
        self._load_skills_data()
    
    def _load_skills_data(self):
        """Load skills data from JSON file"""
        try:
            with open(self.skills_file_path, 'r') as f:
                self._skills_data = json.load(f)
            logger.info("Skills metadata loaded successfully", file_path=str(self.skills_file_path))
        except Exception as e:
            logger.error("Failed to load skills metadata", error=str(e))
            raise ValidationError(f"Failed to load skills metadata: {str(e)}")
    
    def get_all_skills(self) -> Dict[str, List[SkillSpec]]:
        """Get all skills organized by color category"""
        skills_by_color = {}
        
        for color, color_data in self._skills_data.items():
            skills = []
            for skill_data in color_data["skills"]:
                skill_spec = SkillSpec(
                    name=skill_data["skill"],
                    color=color,
                    block_type=skill_data["block_type"],
                    example_question=skill_data["example_question"],
                    description=skill_data["description"],
                    icon_url=skill_data["icon_url"],
                    media_suggestion=skill_data.get("media_suggestion")
                )
                skills.append(skill_spec)
            
            skills_by_color[color] = skills
        
        return skills_by_color
    
    def get_skills_by_color(self, color: str) -> List[SkillSpec]:
        """Get all skills for a specific color category"""
        if color not in self._skills_data:
            raise ValidationError(f"Unknown color category: {color}")
        
        skills = []
        for skill_data in self._skills_data[color]["skills"]:
            skill_spec = SkillSpec(
                name=skill_data["skill"],
                color=color,
                block_type=skill_data["block_type"],
                example_question=skill_data["example_question"],
                description=skill_data["description"],
                icon_url=skill_data["icon_url"],
                media_suggestion=skill_data.get("media_suggestion")
            )
            skills.append(skill_spec)
        
        return skills
    
    def get_skill_by_name(self, skill_name: str) -> Optional[SkillSpec]:
        """Get a specific skill by name"""
        for color, color_data in self._skills_data.items():
            for skill_data in color_data["skills"]:
                if skill_data["skill"] == skill_name:
                    return SkillSpec(
                        name=skill_data["skill"],
                        color=color,
                        block_type=skill_data["block_type"],
                        example_question=skill_data["example_question"],
                        description=skill_data["description"],
                        icon_url=skill_data["icon_url"],
                        media_suggestion=skill_data.get("media_suggestion")
                    )
        return None
    
    def get_skills_by_block_type(self, block_type: str) -> List[SkillSpec]:
        """Get all skills that map to a specific block type"""
        skills = []
        for color, color_data in self._skills_data.items():
            for skill_data in color_data["skills"]:
                if skill_data["block_type"] == block_type:
                    skill_spec = SkillSpec(
                        name=skill_data["skill"],
                        color=color,
                        block_type=skill_data["block_type"],
                        example_question=skill_data["example_question"],
                        description=skill_data["description"],
                        icon_url=skill_data["icon_url"],
                        media_suggestion=skill_data.get("media_suggestion")
                    )
                    skills.append(skill_spec)
        
        return skills
    
    def get_color_info(self, color: str) -> Dict:
        """Get information about a color category"""
        if color not in self._skills_data:
            raise ValidationError(f"Unknown color category: {color}")
        
        return {
            "category": self._skills_data[color]["category"],
            "description": self._skills_data[color]["description"],
            "usage": self._skills_data[color]["usage"],
            "skill_count": len(self._skills_data[color]["skills"])
        }
    
    def validate_skill_sequence(self, skill_names: List[str]) -> bool:
        """Validate that a sequence of skills follows cognitive progression"""
        # Get colors for each skill
        skill_colors = []
        for skill_name in skill_names:
            skill = self.get_skill_by_name(skill_name)
            if skill:
                skill_colors.append(skill.color)
            else:
                logger.warning("Unknown skill in sequence", skill_name=skill_name)
                return False
        
        # Check for logical progression (loose validation)
        color_order = ["Green", "Blue", "Yellow", "Orange", "Red"]
        color_indices = [color_order.index(color) for color in skill_colors if color in color_order]
        
        # Allow some flexibility - just ensure we don't jump backwards too much
        for i in range(1, len(color_indices)):
            if color_indices[i] < color_indices[i-1] - 1:  # Allow 1 step backward
                logger.info("Skill sequence may not follow optimal progression", 
                           skills=skill_names, colors=skill_colors)
                return False
        
        return True


# Global instance
skill_metadata = SkillMetadataManager()