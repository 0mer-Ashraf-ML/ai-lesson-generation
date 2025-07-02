import random
from typing import List, Dict, Optional
from app.core.skills.enhanced_metadata import enhanced_skill_metadata
from app.utils.exceptions import SkillSelectionError
from app.models.lesson import SkillSpec, GenerationContext
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedSkillSelector:
    """Enhanced skill selector using framework structure and subject awareness"""
    
    def __init__(self):
        self.metadata = enhanced_skill_metadata
    
    def select_skills_for_lesson(
        self,
        difficulty: float,
        step_count: int,
        subject: str,
        topic: str = None,
        preferred_blocks: Optional[List[str]] = None
    ) -> List[SkillSpec]:
        """
        Select skills using enhanced framework structure
        
        Args:
            difficulty: 0.0-1.0 difficulty level (controls complexity, not color filtering)
            step_count: Number of blocks to generate
            subject: Subject area for context-aware selection
            topic: Specific topic (future use for topic-relevance)
            preferred_blocks: Optional block type preferences
            
        Returns:
            List of selected SkillSpec objects
        """
        try:
            logger.info(
                "Enhanced skill selection starting",
                difficulty=difficulty,
                step_count=step_count,
                subject=subject
            )
            
            # Get subject preferences
            subject_preferences = self.metadata.get_skills_for_subject_preference(subject)
            
            # Get difficulty level for complexity guidance
            difficulty_level = self.metadata.map_difficulty_to_level(difficulty)
            
            # Select skills with cognitive progression awareness
            selected_skills = self._select_with_progression_logic(
                step_count=step_count,
                subject_preferences=subject_preferences,
                difficulty_level=difficulty_level,
                preferred_blocks=preferred_blocks
            )
            
            logger.info(
                "Enhanced skill selection completed",
                selected_skills=[skill.name for skill in selected_skills],
                colors=[skill.color for skill in selected_skills],
                difficulty_level=difficulty_level
            )
            
            return selected_skills
            
        except Exception as e:
            logger.error("Enhanced skill selection failed", error=str(e))
            raise SkillSelectionError(f"Failed to select skills: {str(e)}")
    
    def _select_with_progression_logic(
        self,
        step_count: int,
        subject_preferences: Dict[str, float],
        difficulty_level: str,
        preferred_blocks: Optional[List[str]] = None
    ) -> List[SkillSpec]:
        """Select skills following loose cognitive progression"""
        
        # Flexible progression - not strict color filtering
        # Based on Paul's guidance that order isn't rigid
        
        all_skills = self._get_all_available_skills()
        selected_skills = []
        
        for i in range(step_count):
            # Get context for this position
            position_context = self._get_position_context(i, step_count)
            
            # Filter available skills
            available_skills = self._filter_skills_for_position(
                all_skills=all_skills,
                position_context=position_context,
                subject_preferences=subject_preferences,
                difficulty_level=difficulty_level,
                preferred_blocks=preferred_blocks,
                position_index=i,
                already_selected=[s.name for s in selected_skills]
            )
            
            if not available_skills:
                # Fallback to any available skill
                available_skills = [s for s in all_skills if s.name not in [sel.name for sel in selected_skills]]
            
            if available_skills:
                # Weight selection by subject preference
                selected_skill = self._weighted_skill_selection(available_skills, subject_preferences)
                selected_skills.append(selected_skill)
        
        return selected_skills
    
    def _get_position_context(self, position: int, total_steps: int) -> Dict[str, any]:
        """Get context about this position in the lesson sequence"""
        
        if position == 0:
            return {
                "role": "opening",
                "preferred_colors": ["Green", "Blue"],  # Starting skills
                "avoid_colors": []
            }
        elif position == total_steps - 1:
            return {
                "role": "concluding", 
                "preferred_colors": ["Red", "Yellow"],  # Application/synthesis
                "avoid_colors": []
            }
        else:
            return {
                "role": "developing",
                "preferred_colors": ["Blue", "Yellow", "Orange"],  # Organizing/analyzing
                "avoid_colors": []
            }
    
    def _filter_skills_for_position(
        self,
        all_skills: List[SkillSpec],
        position_context: Dict,
        subject_preferences: Dict[str, float],
        difficulty_level: str,
        preferred_blocks: Optional[List[str]],
        position_index: int,
        already_selected: List[str]
    ) -> List[SkillSpec]:
        """Filter skills appropriate for this position"""
        
        filtered_skills = []
        
        for skill in all_skills:
            # Skip already selected
            if skill.name in already_selected:
                continue
            
            # Check block type preference
            if preferred_blocks and position_index < len(preferred_blocks):
                if skill.block_type != preferred_blocks[position_index]:
                    continue
            
            # Loose color preference (not strict filtering)
            color_score = 1.0
            if skill.color in position_context.get("preferred_colors", []):
                color_score = 1.5  # Boost preferred colors
            elif skill.color in position_context.get("avoid_colors", []):
                color_score = 0.3  # Reduce avoided colors
            
            # Subject preference
            subject_score = subject_preferences.get(skill.name, 0.5)
            
            # Difficulty appropriateness - check if skill has this difficulty level
            difficulty_guidance = self.metadata.get_difficulty_guidance(skill.name, difficulty_level)
            difficulty_score = 1.2 if difficulty_guidance else 0.8
            
            # Combined score
            combined_score = color_score * subject_score * difficulty_score
            
            if combined_score > 0.4:  # Threshold for inclusion
                skill._selection_score = combined_score  # Store for weighted selection
                filtered_skills.append(skill)
        
        return filtered_skills
    
    def _weighted_skill_selection(self, available_skills: List[SkillSpec], subject_preferences: Dict[str, float]) -> SkillSpec:
        """Select skill using weighted probability"""
        
        if len(available_skills) == 1:
            return available_skills[0]
        
        # Use selection scores if available
        if hasattr(available_skills[0], '_selection_score'):
            weights = [getattr(skill, '_selection_score', 1.0) for skill in available_skills]
        else:
            # Fallback to subject preferences
            weights = [subject_preferences.get(skill.name, 0.5) for skill in available_skills]
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(available_skills)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for skill, weight in zip(available_skills, weights):
            cumulative += weight
            if r <= cumulative:
                return skill
        
        return available_skills[-1]  # Fallback
    
    def _get_all_available_skills(self) -> List[SkillSpec]:
        """Get all available skills from enhanced metadata"""
        all_skills = []
        
        for color, color_data in self.metadata._skills_data.items():
            for skill_info in color_data["skills"]:
                skill_spec = SkillSpec(
                    name=skill_info["skill"],
                    color=color,
                    block_type=skill_info["block_type"],
                    example_question=skill_info["example_question"],
                    description=skill_info["description"],
                    icon_url=skill_info["icon_url"],
                    media_suggestion=skill_info.get("media_suggestion")
                )
                all_skills.append(skill_spec)
        
        return all_skills
    
    def select_complexity_level(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        position: int,
        total_steps: int,
        previous_levels: List[str] = None
    ) -> str:
        """
        Select appropriate cognitive complexity level based on multiple factors
        
        Args:
            skill: The thinking skill
            context: Generation context
            position: Position in the lesson sequence
            total_steps: Total steps in the lesson
            previous_levels: Previously used complexity levels
            
        Returns:
            Complexity level string (getting_started, thinking_harder, stretching_thinking)
        """
        previous_levels = previous_levels or []
        
        # Default mapping based on difficulty
        base_level = self.metadata.map_difficulty_to_level(context.difficulty)
        
        # Adjust based on grade level
        grade_number = self._extract_grade_number(context.grade)
        
        # Early grades (1-3) should use simpler complexity by default
        if grade_number and grade_number <= 3 and base_level == "stretching_thinking":
            base_level = "thinking_harder"
        
        # Higher grades (7+) can handle more complex tasks
        if grade_number and grade_number >= 7 and base_level == "getting_started":
            base_level = "thinking_harder"
        
        # Adjust based on position in lesson
        # First step should be simpler to build confidence
        if position == 0 and base_level == "stretching_thinking":
            return "thinking_harder"
        
        # Last step can be more challenging to extend thinking
        if position == total_steps - 1 and base_level == "getting_started":
            return "thinking_harder"
        
        # Avoid using the same level for more than 2 consecutive steps
        if len(previous_levels) >= 2:
            if previous_levels[-1] == previous_levels[-2] == base_level:
                # Choose a different level
                if base_level == "getting_started":
                    return "thinking_harder"
                elif base_level == "stretching_thinking":
                    return "thinking_harder"
                else:
                    # If we're at thinking_harder, choose randomly between simpler and more complex
                    return random.choice(["getting_started", "stretching_thinking"])
        
        # Adjust based on skill color
        # Red skills are naturally more complex
        if skill.color == "Red" and base_level == "getting_started":
            return "thinking_harder"
        
        # Green skills are naturally simpler
        if skill.color == "Green" and base_level == "stretching_thinking":
            return "thinking_harder"
        
        return base_level

    def _extract_grade_number(self, grade: str) -> Optional[int]:
        """Extract numeric grade level from grade string"""
        try:
            if 'Year' in grade:
                return int(''.join(filter(str.isdigit, grade)))
            elif 'Grade' in grade:
                return int(''.join(filter(str.isdigit, grade)))
            return None
        except (ValueError, TypeError):
            return None


# Global instance  
enhanced_skill_selector = EnhancedSkillSelector()