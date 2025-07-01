from typing import Dict, Any, Optional
import random
from app.models.lesson import SkillSpec, GenerationContext
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ScaffoldingAssessor:
    """Determines when full scaffolding is needed vs simple prompts"""
    
    def __init__(self):
        # Skills that often work well with simple prompts
        self.simple_prompt_candidates = {
            "Green": ["Identify", "Retrieve", "Recognize", "Extract"],
            "Yellow": ["Explain", "Exemplify"],
            "Blue": ["Compare"],  # Sometimes just discussion works
        }
        
        # Skills that almost always benefit from scaffolding
        self.scaffold_required = {
            "Red": ["Hypothesise", "Judge", "Combine", "Imagine"],
            "Orange": ["Target Vocabulary", "Verbs", "Adjectives"],
            "Blue": ["Categorise", "Sequence", "Rank"],  # Need structure
        }
        
        # Time estimates per activity type (minutes)
        self.time_estimates = {
            "MapIt": 15,
            "SayIt": 10, 
            "BuildIt": 20,
            "Prompt": 5
        }
    
    def should_use_full_scaffold(
        self,
        skill: SkillSpec,
        context: GenerationContext,
        available_time_minutes: Optional[int] = None,
        sequence_position: int = 0,
        total_steps: int = 3,
        previous_scaffolds_count: int = 0
    ) -> bool:
        """
        Determine if this step needs full scaffolding or can use simple prompt
        
        Args:
            skill: The thinking skill being assessed
            context: Generation context
            available_time_minutes: Total time available for lesson
            sequence_position: Position in lesson (0-based)
            total_steps: Total number of steps in lesson
            previous_scaffolds_count: Number of full scaffolds already used
            
        Returns:
            True if full scaffold needed, False for simple prompt
        """
        try:
            # 1. Time pressure assessment
            if available_time_minutes:
                avg_time_per_step = available_time_minutes / total_steps
                remaining_steps = total_steps - sequence_position
                time_per_remaining_step = (available_time_minutes - (sequence_position * 10)) / remaining_steps if remaining_steps > 0 else 10
                
                # If time is very tight, prefer prompts
                if time_per_remaining_step < 8:
                    logger.info(f"Time pressure: {time_per_remaining_step:.1f}min/step, using prompt for {skill.name}")
                    return False
                
                # BuildIt activities need more time - skip if insufficient
                if skill.block_type == "BuildIt" and time_per_remaining_step < 15:
                    logger.info(f"Insufficient time for BuildIt ({time_per_remaining_step:.1f}min), using prompt for {skill.name}")
                    return False
            
            # 2. Skills that require scaffolding
            if skill.color in self.scaffold_required:
                if skill.name in self.scaffold_required[skill.color]:
                    return True
            
            # 3. Skills that work well with simple prompts
            if skill.color in self.simple_prompt_candidates:
                if skill.name in self.simple_prompt_candidates[skill.color]:
                    # Use variety - don't make all prompts
                    if previous_scaffolds_count == 0:
                        return True  # Ensure at least one scaffold in lesson
                    # 40% chance of prompt for variety
                    use_prompt = random.random() < 0.4
                    if use_prompt:
                        logger.info(f"Using prompt for variety: {skill.name}")
                        return False
            
            # 4. Lesson position logic
            # Always scaffold the first step if it's complex
            if sequence_position == 0 and skill.color in ["Yellow", "Orange", "Red"]:
                return True
            
            # Last step - prefer application (scaffold for Red skills)
            if sequence_position == total_steps - 1 and skill.color == "Red":
                return True
            
            # 5. Variety management
            # If we've had too many scaffolds in a row, consider a prompt
            if previous_scaffolds_count >= 2 and skill.color in ["Green", "Blue"]:
                if random.random() < 0.3:  # 30% chance
                    logger.info(f"Breaking scaffold sequence with prompt: {skill.name}")
                    return False
            
            # 6. Subject-specific logic
            if context.subject == "Mathematics":
                # Math often benefits from structured activities
                if skill.name in ["Sequence", "Categorise", "Compare"]:
                    return True
            
            elif context.subject == "English":
                # Language work often needs scaffolding
                if skill.color == "Orange":  # Language skills
                    return True
            
            # 7. Default decision
            # BuildIt almost always gets scaffolding (when time allows)
            if skill.block_type == "BuildIt":
                return True
            
            # Most other cases get scaffolding
            return True
            
        except Exception as e:
            logger.error("Error in scaffolding assessment", error=str(e), skill=skill.name)
            return True  # Default to scaffolding on error
    
    def generate_simple_prompt(
        self,
        skill: SkillSpec,
        context: GenerationContext
    ) -> Dict[str, Any]:
        """Generate a simple prompt instead of full scaffold"""
        
        # Skill-specific prompt templates
        prompt_templates = {
            # Green skills - foundational
            "Identify": [
                f"Look at the information about {context.topic}. What key elements can you identify?",
                f"Point out the main features you notice in {context.topic}.",
                f"What important details stand out when you examine {context.topic}?"
            ],
            "Retrieve": [
                f"Think back to what we've learned about {context.topic}. What do you remember?",
                f"What prior knowledge do you have about {context.topic}?",
                f"Recall what you already know that might help with {context.topic}."
            ],
            "Recognize": [
                f"What patterns or familiar elements do you recognize in {context.topic}?",
                f"Have you seen anything similar to {context.topic} before?",
                f"What aspects of {context.topic} look familiar to you?"
            ],
            
            # Blue skills - organizing
            "Compare": [
                f"How is {context.topic} similar to or different from what we studied before?",
                f"What similarities and differences do you notice in {context.topic}?",
                f"Compare {context.topic} to something you already understand."
            ],
            
            # Yellow skills - critical thinking
            "Explain": [
                f"Can you explain in your own words how {context.topic} works?",
                f"What's your understanding of {context.topic}? Explain it to a friend.",
                f"Break down {context.topic} and explain the key ideas."
            ],
            "Exemplify": [
                f"Can you give a specific example that shows {context.topic}?",
                f"What real-world examples demonstrate {context.topic}?",
                f"Think of an example that illustrates {context.topic}."
            ]
        }
        
        # Get prompts for this skill
        skill_prompts = prompt_templates.get(skill.name, [
            f"Use {skill.name} thinking about {context.topic}.",
            f"Apply {skill.name} to understand {context.topic} better.",
            f"How can {skill.name} help us explore {context.topic}?"
        ])
        
        # Choose a prompt (randomly for variety)
        selected_prompt = random.choice(skill_prompts)
        
        # Generate follow-up questions based on skill type
        follow_ups = self._generate_follow_up_questions(skill, context)
        
        return {
            "type": "simple_prompt",
            "main_prompt": selected_prompt,
            "follow_up_questions": follow_ups,
            "skill": skill.name,
            "duration_minutes": 5,
            "interaction_type": self._get_interaction_type(skill),
            "success_indicators": self._get_success_indicators(skill)
        }
    
    def _generate_follow_up_questions(self, skill: SkillSpec, context: GenerationContext) -> list:
        """Generate follow-up questions to deepen thinking"""
        
        follow_up_templates = {
            "Identify": [
                "What else do you notice?",
                "Are there any details you missed?",
                "What's the most important element you identified?"
            ],
            "Retrieve": [
                "What else can you remember?",
                "How does this connect to previous learning?",
                "What questions does this raise for you?"
            ],
            "Compare": [
                "What's the most significant similarity?",
                "Which difference surprises you most?",
                "How does this comparison help your understanding?"
            ],
            "Explain": [
                "Can you give an example to support your explanation?",
                "What would happen if...?",
                "How would you explain this to someone younger?"
            ]
        }
        
        return follow_up_templates.get(skill.name, [
            "What makes you think that?",
            "Can you elaborate on that idea?",
            "What questions does this raise?"
        ])
    
    def _get_interaction_type(self, skill: SkillSpec) -> str:
        """Determine the best interaction type for this skill prompt"""
        
        interaction_types = {
            "Green": "think_pair_share",  # Good for foundation skills
            "Blue": "whole_class_discussion",  # Good for organizing ideas
            "Yellow": "small_group_discussion",  # Good for critical thinking
            "Orange": "individual_then_share",  # Good for language work
            "Red": "collaborative_thinking"  # Good for application
        }
        
        return interaction_types.get(skill.color, "whole_class_discussion")
    
    def _get_success_indicators(self, skill: SkillSpec) -> list:
        """Define what success looks like for this prompt"""
        
        success_indicators = {
            "Identify": [
                "Students point out specific, relevant details",
                "Responses show careful observation",
                "Key elements are accurately identified"
            ],
            "Retrieve": [
                "Students recall relevant prior knowledge",
                "Connections to previous learning are made",
                "Accurate information is remembered"
            ],
            "Compare": [
                "Both similarities and differences are noted",
                "Comparisons are specific and accurate",
                "Students justify their comparisons"
            ],
            "Explain": [
                "Explanations are clear and logical",
                "Students use appropriate vocabulary",
                "Understanding is demonstrated through explanation"
            ]
        }
        
        return success_indicators.get(skill.name, [
            f"Students demonstrate {skill.name} thinking",
            "Responses show understanding of the concept",
            "Students engage meaningfully with the topic"
        ])
    
    def estimate_activity_time(
        self,
        use_scaffold: bool,
        skill: SkillSpec,
        context: GenerationContext
    ) -> int:
        """Estimate how long this activity will take"""
        
        if not use_scaffold:
            return self.time_estimates["Prompt"]
        
        base_time = self.time_estimates.get(skill.block_type, 12)
        
        # Adjust for difficulty
        if context.difficulty <= 0.3:
            return int(base_time * 0.8)  # Simpler activities
        elif context.difficulty >= 0.7:
            return int(base_time * 1.2)  # More complex activities
        
        return base_time
    
    def get_scaffolding_summary(
        self,
        scaffold_decisions: list,
        total_time_estimate: int
    ) -> Dict[str, Any]:
        """Generate summary of scaffolding decisions for logging/debugging"""
        
        full_scaffolds = sum(1 for decision in scaffold_decisions if decision["use_scaffold"])
        simple_prompts = len(scaffold_decisions) - full_scaffolds
        
        return {
            "total_activities": len(scaffold_decisions),
            "full_scaffolds": full_scaffolds,
            "simple_prompts": simple_prompts,
            "total_time_estimate": total_time_estimate,
            "avg_time_per_activity": total_time_estimate / len(scaffold_decisions) if scaffold_decisions else 0,
            "scaffold_ratio": full_scaffolds / len(scaffold_decisions) if scaffold_decisions else 0,
            "decisions": scaffold_decisions
        }


# Global instance
scaffolding_assessor = ScaffoldingAssessor()