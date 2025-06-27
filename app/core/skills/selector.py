import random
from typing import List, Dict, Optional
from app.core.skills.metadata import skill_metadata
from app.models.lesson import SkillSpec
from app.utils.exceptions import SkillSelectionError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SkillSelector:
    """Selects appropriate thinking skills based on lesson parameters"""
    
    def __init__(self):
        self.metadata = skill_metadata
    
    def select_skills_for_lesson(
        self, 
        difficulty: float, 
        step_count: int,
        preferred_blocks: Optional[List[str]] = None,
        subject: Optional[str] = None
    ) -> List[SkillSpec]:
        """
        Select appropriate skills for a lesson based on difficulty and step count
        
        Args:
            difficulty: 0.0 (easy) to 1.0 (hard)
            step_count: Number of blocks to generate (2-5)
            preferred_blocks: Optional list of preferred block types
            subject: Subject area (for future customization)
        
        Returns:
            List of SkillSpec objects in sequence
        """
        try:
            # Determine available color categories based on difficulty
            available_colors = self._get_colors_for_difficulty(difficulty)
            
            # Select skills following cognitive progression
            selected_skills = self._select_progressive_skills(
                available_colors, 
                step_count, 
                preferred_blocks
            )
            
            logger.info(
                "Skills selected for lesson",
                difficulty=difficulty,
                step_count=step_count,
                selected_skills=[skill.name for skill in selected_skills],
                colors=[skill.color for skill in selected_skills]
            )
            
            return selected_skills
            
        except Exception as e:
            logger.error("Error selecting skills", error=str(e))
            raise SkillSelectionError(f"Failed to select skills: {str(e)}")
    
    def _get_colors_for_difficulty(self, difficulty: float) -> List[str]:
        """Determine which color categories are appropriate for difficulty level"""
        # Map difficulty to color combinations
        if difficulty <= 0.3:  # Easy - focus on foundational skills
            return ["Green", "Blue"]
        elif difficulty <= 0.5:  # Medium-easy - add some critical thinking
            return ["Green", "Blue", "Yellow"]
        elif difficulty <= 0.7:  # Medium-hard - include language and application
            return ["Blue", "Yellow", "Orange", "Red"]
        else:  # Hard - focus on higher-order thinking
            return ["Yellow", "Orange", "Red"]
    
    def _select_progressive_skills(
        self, 
        available_colors: List[str], 
        step_count: int,
        preferred_blocks: Optional[List[str]] = None
    ) -> List[SkillSpec]:
        """Select skills following cognitive progression"""
        
        # Define progression logic (loose ordering)
        color_progression = ["Green", "Blue", "Yellow", "Orange", "Red"]
        
        # Filter available colors to maintain some progression
        ordered_colors = [color for color in color_progression if color in available_colors]
        
        selected_skills = []
        
        for i in range(step_count):
            # Determine color for this step
            if i == 0 and "Green" in ordered_colors:
                # First step - prefer Green for starting
                target_colors = ["Green"]
            elif i == step_count - 1 and "Red" in ordered_colors:
                # Last step - prefer Red for application
                target_colors = ["Red"]
            else:
                # Middle steps - use progression logic
                if i < len(ordered_colors):
                    target_colors = ordered_colors[i:i+2]  # Allow some flexibility
                else:
                    target_colors = ordered_colors[-2:]  # Use later colors
            
            # Select skill from target colors
            skill = self._select_skill_from_colors(
                target_colors, 
                preferred_blocks, 
                i,
                selected_skills
            )
            
            if skill:
                selected_skills.append(skill)
            else:
                # Fallback - select any available skill
                fallback_skill = self._select_fallback_skill(available_colors, selected_skills)
                if fallback_skill:
                    selected_skills.append(fallback_skill)
        
        return selected_skills
    
    def _select_skill_from_colors(
        self, 
        target_colors: List[str], 
        preferred_blocks: Optional[List[str]],
        step_index: int,
        already_selected: List[SkillSpec]
    ) -> Optional[SkillSpec]:
        """Select a skill from target colors"""
        
        # Get already used skill names to avoid repetition
        used_skills = {skill.name for skill in already_selected}
        
        # Collect candidate skills
        candidates = []
        for color in target_colors:
            color_skills = self.metadata.get_skills_by_color(color)
            
            # Filter by preferred blocks if specified
            if preferred_blocks and step_index < len(preferred_blocks):
                preferred_block = preferred_blocks[step_index]
                color_skills = [s for s in color_skills if s.block_type == preferred_block]
            
            # Filter out already used skills
            color_skills = [s for s in color_skills if s.name not in used_skills]
            
            candidates.extend(color_skills)
        
        # Select randomly from candidates
        if candidates:
            return random.choice(candidates)
        
        return None
    
    def _select_fallback_skill(
        self, 
        available_colors: List[str], 
        already_selected: List[SkillSpec]
    ) -> Optional[SkillSpec]:
        """Select any available skill as fallback"""
        
        used_skills = {skill.name for skill in already_selected}
        
        all_candidates = []
        for color in available_colors:
            color_skills = self.metadata.get_skills_by_color(color)
            color_skills = [s for s in color_skills if s.name not in used_skills]
            all_candidates.extend(color_skills)
        
        if all_candidates:
            return random.choice(all_candidates)
        
        return None
    
    def get_skills_by_block_type(self, block_type: str) -> List[SkillSpec]:
        """Get all skills that map to a specific block type"""
        return self.metadata.get_skills_by_block_type(block_type)
    
    def validate_skill_sequence(self, skills: List[SkillSpec]) -> bool:
        """Validate that skill sequence follows good cognitive progression"""
        skill_names = [skill.name for skill in skills]
        return self.metadata.validate_skill_sequence(skill_names)


# Global instance
skill_selector = SkillSelector()