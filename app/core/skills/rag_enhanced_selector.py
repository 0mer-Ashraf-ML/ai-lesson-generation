from typing import List, Dict, Optional, Set
import random
from pinecone import Pinecone
from app.config import settings
from app.core.rag.embedder import text_embedder
from app.models.lesson import SkillSpec
from app.utils.exceptions import SkillSelectionError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RAGEnhancedSkillSelector:
    """Skill selector that uses RAG to dynamically discover available skills"""
    
    def __init__(self):
        self._pinecone = Pinecone(api_key=settings.pinecone_api_key)
        self._index = None
        self._skills_cache = {}  # Cache discovered skills
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            indexes = self._pinecone.list_indexes().names()
            if settings.pinecone_index_name in indexes:
                self._index = self._pinecone.Index(settings.pinecone_index_name)
                logger.info("RAG skill selector connected to Pinecone")
            else:
                logger.warning(f"Pinecone index '{settings.pinecone_index_name}' not found")
        except Exception as e:
            logger.error("Failed to initialize Pinecone for skill selection", error=str(e))
    
    async def select_skills_for_lesson(
        self,
        difficulty: float,
        step_count: int,
        subject: str,
        topic: str = None,
        preferred_blocks: Optional[List[str]] = None
    ) -> List[SkillSpec]:
        """
        Select skills using RAG while preserving color and block type from metadata
        
        Args:
            difficulty: 0.0-1.0 difficulty level
            step_count: Number of blocks to generate
            subject: Subject area
            topic: Specific topic
            preferred_blocks: Optional block type preferences
            
        Returns:
            List of selected SkillSpec objects
        """
        try:
            logger.info(
                "Starting enhanced skill selection",
                difficulty=difficulty,
                step_count=step_count,
                subject=subject,
                topic=topic,
                preferred_blocks=preferred_blocks
            )
            
            # Get all available skills from the metadata
            all_skills = self._get_all_skills_from_metadata()
            if not all_skills:
                logger.warning("No skills found in metadata, falling back to default selection")
                return await self._fallback_skill_selection(difficulty, step_count, preferred_blocks)
            
            # Determine scaffold sequence
            if preferred_blocks and len(preferred_blocks) >= step_count:
                scaffold_sequence = preferred_blocks[:step_count]
            else:
                scaffold_sequence = self._generate_varied_scaffold_sequence(step_count, difficulty)
            
            logger.info(f"Using scaffold sequence: {scaffold_sequence}")
            
            # Select skills based on scaffold sequence
            selected_skills = []
            
            for i, block_type in enumerate(scaffold_sequence):
                # Find skills that match this block type
                matching_skills = [s for s in all_skills if s.block_type == block_type]
                
                if not matching_skills:
                    logger.warning(f"No skills found for block type: {block_type}")
                    continue
                
                # Select a skill for this position
                selected_skill = self._select_skill_for_position(
                    matching_skills,
                    subject,
                    topic,
                    position=i,
                    already_selected=[s.name for s in selected_skills],
                    difficulty=difficulty
                )
                
                if selected_skill:
                    selected_skills.append(selected_skill)
                
            # If we don't have enough skills, add more
            while len(selected_skills) < step_count:
                # Get skills that haven't been used yet
                used_names = [s.name for s in selected_skills]
                available_skills = [s for s in all_skills if s.name not in used_names]
                
                if not available_skills:
                    available_skills = all_skills  # If all are used, allow repeats
                
                # Select a random skill
                selected_skills.append(random.choice(available_skills))
            
            logger.info(
                "Enhanced skill selection completed",
                selected_skills=[skill.name for skill in selected_skills],
                colors=[skill.color for skill in selected_skills],
                block_types=[skill.block_type for skill in selected_skills]
            )
            
            return selected_skills[:step_count]  # Ensure we only return the requested number
            
        except Exception as e:
            logger.error("Enhanced skill selection failed", error=str(e))
            return await self._fallback_skill_selection(difficulty, step_count, preferred_blocks)

    def _ensure_correct_icon_url(self, skill_name: str, color: str) -> str:
        """Ensure the icon URL is correctly formatted for the skill and color"""
        # Standard format for icon URLs
        return f"https://cdn.structural-learning.com/icons/{color.lower()}_{skill_name.lower().replace(' ', '_')}.svg"

    def _get_all_skills_from_metadata(self) -> List[SkillSpec]:
        """Get all available skills from the metadata with correct icon URLs"""
        try:
            # Import the enhanced metadata
            from app.core.skills.enhanced_metadata import enhanced_skill_metadata
            
            all_skills = []
            
            # Go through each color category
            for color, color_data in enhanced_skill_metadata._skills_data.items():
                # Go through each skill in this color
                for skill_data in color_data.get("skills", []):
                    # Generate the correct icon URL based on color and skill name
                    icon_url = self._ensure_correct_icon_url(skill_data["skill"], color)
                    
                    # Create skill spec with color and block_type from metadata
                    skill_spec = SkillSpec(
                        name=skill_data["skill"],
                        color=color,  # Important: Use color from metadata
                        block_type=skill_data["block_type"],  # Important: Use block_type from metadata
                        example_question=skill_data["example_question"],
                        description=skill_data["description"],
                        icon_url=icon_url,  # Use the corrected icon URL
                        media_suggestion=skill_data.get("media_suggestion")
                    )
                    all_skills.append(skill_spec)
            
            logger.info(f"Loaded {len(all_skills)} skills from metadata with correct icon URLs")
            return all_skills
            
        except Exception as e:
            logger.error("Error loading skills from metadata", error=str(e))
            return []
    
    def _select_skill_for_position(
        self,
        matching_skills: List[SkillSpec],
        subject: str,
        topic: str = None,
        position: int = 0,
        already_selected: List[str] = None,
        difficulty: float = 0.5
    ) -> Optional[SkillSpec]:
        """Select an appropriate skill for this position in the lesson"""
        if not matching_skills:
            return None
            
        already_selected = already_selected or []
        
        # Filter out already selected skills
        available_skills = [s for s in matching_skills if s.name not in already_selected]
        
        if not available_skills:
            available_skills = matching_skills  # If all used, allow repeats
        
        # Get subject preferences
        subject_preferences = self._get_subject_preferences(subject)
        
        # Calculate scores for each skill
        skill_scores = []
        for skill in available_skills:
            # Base score
            score = 1.0
            
            # Subject preference boost
            subject_boost = subject_preferences.get(skill.name, 0.5)
            score *= subject_boost
            
            # Position-based boost
            if position == 0:
                # For first position, prefer Green and Blue skills
                if skill.color == "Green":
                    score *= 2.0
                elif skill.color == "Blue":
                    score *= 1.5
            elif position >= 2:  # Later positions
                # For later positions, prefer Red and Yellow skills
                if skill.color == "Red":
                    score *= 2.0
                elif skill.color == "Yellow":
                    score *= 1.5
            
            # Add randomness to avoid repetition
            score *= (0.8 + random.random() * 0.4)  # Between 0.8 and 1.2
            
            skill_scores.append((skill, score))
        
        # Sort by score and select the highest
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        
        if skill_scores:
            return skill_scores[0][0]
        
        return random.choice(available_skills)

    def _get_subject_preferences(self, subject: str) -> Dict[str, float]:
        """Get subject-specific skill preferences"""
        # These could be refined with curricular analysis
        subject_preferences = {
            "Science": {
                "Categorise": 0.9,
                "Compare": 0.8,
                "Hypothesise": 0.9,
                "Explain": 0.8,
                "Sequence": 0.7
            },
            "Mathematics": {
                "Sequence": 0.9,
                "Compare": 0.8,
                "Categorise": 0.7,
                "Rank": 0.8
            },
            "English": {
                "Explain": 0.9,
                "Elaborate": 0.8,
                "Target Vocabulary": 0.9,
                "Adjectives": 0.8
            },
            "History": {
                "Sequence": 0.9,
                "Explain": 0.8,
                "Compare": 0.7,
                "New Perspective": 0.8
            },
            "Geography": {
                "Categorise": 0.9,
                "Compare": 0.8,
                "Connect": 0.7,
                "Explain": 0.7
            }
        }
        
        return subject_preferences.get(subject, {})
    def _select_appropriate_skill(
        self,
        matching_skills: List[SkillSpec],
        subject: str,
        topic: str,
        difficulty: float,
        position: int,
        already_selected: List[SkillSpec]
    ) -> Optional[SkillSpec]:
        """Select an appropriate skill for this position"""
        
        # Avoid repeating skills
        unused_skills = [s for s in matching_skills if s.name not in [skill.name for skill in already_selected]]
        if not unused_skills:
            unused_skills = matching_skills  # If all are used, allow repeats
        
        # Adjust preferences based on subject
        subject_preferences = self._get_subject_preferences(subject)
        
        # Adjust preferences based on position
        if position == 0:
            # Prefer Green or Blue skills for first position
            color_boost = {"Green": 2.0, "Blue": 1.5}
        elif position == len(already_selected):
            # Prefer Red or Yellow skills for last position
            color_boost = {"Red": 2.0, "Yellow": 1.5}
        else:
            # No strong color preference for middle positions
            color_boost = {}
        
        # Calculate scores for each skill
        skill_scores = []
        for skill in unused_skills:
            # Base score
            score = 1.0
            
            # Boost based on subject preferences
            subject_boost = subject_preferences.get(skill.name, 0.5)
            score *= subject_boost
            
            # Boost based on position/color
            color_multiplier = color_boost.get(skill.color, 1.0)
            score *= color_multiplier
            
            # Add a random factor to avoid always picking the same skills
            score *= (0.8 + random.random() * 0.4)  # Random factor between 0.8 and 1.2
            
            skill_scores.append((skill, score))
        
        # Sort by score and select the best
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        
        if skill_scores:
            return skill_scores[0][0]
        
        return None

    def _determine_needed_scaffolds(
        self, 
        preferred_blocks: Optional[List[str]], 
        difficulty: float, 
        step_count: int
    ) -> List[str]:
        """Determine which scaffold types we actually need to generate skills for"""
        
        if preferred_blocks:
            # Convert preferred blocks to scaffold format and get unique values
            needed = set()
            for block in preferred_blocks:
                if block == "MapIt":
                    needed.add("mapit")
                elif block == "SayIt":
                    needed.add("sayit")
                elif block == "BuildIt":
                    needed.add("buildit")
            return list(needed)
        else:
            # If no preferences, determine based on difficulty what we might need
            if difficulty <= 0.3:
                return ["mapit", "sayit"]  # Simple lessons
            elif difficulty <= 0.7:
                return ["mapit", "sayit", "buildit"]  # Balanced lessons
            else:
                return ["sayit", "buildit", "mapit"]  # Advanced lessons
    
    async def _discover_skills_from_rag(
        self,
        subject: str,
        topic: str = None,
        difficulty: float = 0.5,
        top_k: int = 5,
        needed_scaffolds: List[str] = None,
        step_count: int = 3
    ) -> Dict[str, List[SkillSpec]]:
        """
        Discover available skills by querying RAG system - OPTIMIZED VERSION
        """
        try:
            if not self._index:
                return {}
            
            # Use provided scaffolds or default to all
            scaffolds_to_process = needed_scaffolds or ["buildit", "sayit", "mapit"]
            
            # Build search query - simpler approach
            query_text = f"{subject} learning activities"
            if topic:
                query_text = f"{subject} {topic} activities"
            
            # Generate embedding ONCE for all scaffold queries
            query_embedding = await text_embedder.embed_text(query_text)
            
            # Search only the needed scaffold types
            all_skills = {}
            
            for scaffold_type in scaffolds_to_process:
                # Query for this scaffold type
                results = self._index.query(
                    vector=query_embedding,  # Reuse same embedding
                    top_k=top_k,  # Reduced number
                    include_values=False,
                    include_metadata=True,
                    filter={
                        "scaffold_type": {"$eq": scaffold_type},
                        "content_type": {"$eq": "pdf"}
                    }
                )
                
                # Extract skills from results (now with difficulty awareness)
                scaffold_skills = self._extract_skills_from_results(
                    results, scaffold_type, difficulty, step_count
                )
                if scaffold_skills:
                    all_skills[scaffold_type] = scaffold_skills
            
            logger.info(
                "Discovered skills from RAG - TARGETED",
                scaffolds_processed=scaffolds_to_process,
                difficulty=difficulty,
                buildit_skills=len(all_skills.get("buildit", [])),
                sayit_skills=len(all_skills.get("sayit", [])),
                mapit_skills=len(all_skills.get("mapit", []))
            )
            
            return all_skills
            
        except Exception as e:
            logger.error("Error discovering skills from RAG", error=str(e))
            return {}
    
    def _extract_skills_from_results(self, results, scaffold_type: str, difficulty: float = 0.5, total_steps: int = 3) -> List[SkillSpec]:
        """Extract skill specifications from Pinecone results"""
        skills = []
        
        # Map scaffold types to block types
        scaffold_to_block = {
            "buildit": "BuildIt",
            "sayit": "SayIt", 
            "mapit": "MapIt"
        }
        
        block_type = scaffold_to_block.get(scaffold_type, scaffold_type.title())
        
        # Define thinking skills based on difficulty and scaffold
        if difficulty <= 0.25:  # Green skills for very easy
            skill_mappings = {
                "mapit": ["Identify", "Retrieve", "Recognize", "Find", "Point Out"],
                "sayit": ["Name", "List", "Recall", "State", "Describe"],
                "buildit": ["Sort", "Match", "Group", "Collect", "Arrange"]
            }
            # For very low difficulty, all skills should be Green
            base_color = "Green"
            
        elif difficulty >= 0.8:  # More advanced skills
            skill_mappings = {
                "mapit": ["Analyze", "Synthesize", "Evaluate", "Compare", "Contrast"],
                "sayit": ["Argue", "Defend", "Critique", "Justify", "Elaborate"], 
                "buildit": ["Design", "Create", "Innovate", "Construct", "Engineer"]
            }
            # For high difficulty, use advanced colors
            base_color = "Orange" if scaffold_type == "sayit" else ("Red" if scaffold_type == "buildit" else "Yellow")
            
        else:  # Standard skills
            skill_mappings = {
                "mapit": ["Categorise", "Compare", "Sequence", "Rank", "Connect"],
                "sayit": ["Explain", "Validate", "Exemplify", "Target Vocabulary", "Elaborate"],
                "buildit": ["Hypothesise", "Judge", "Combine", "Imagine", "Integrate"]
            }
            # Standard color mapping
            color_map = {"mapit": "Blue", "sayit": "Yellow", "buildit": "Red"}
            base_color = color_map.get(scaffold_type, "Blue")
        
        available_skills = skill_mappings.get(scaffold_type, ["Apply", "Analyze", "Create"])
        
        # Create skill specs for each available skill (up to 5)
        for i, skill_name in enumerate(available_skills[:5]):
            # For low difficulty, keep Green for all skills
            if difficulty <= 0.25:
                color = "Green"
            else:
                color = base_color
            
            skill_spec = SkillSpec(
                name=skill_name,
                color=color,
                block_type=block_type,
                example_question=self._generate_example_question(skill_name, scaffold_type),
                description=self._generate_description_for_skill(skill_name, scaffold_type),
                icon_url=f"https://cdn.structural-learning.com/icons/{color.lower()}_{skill_name.lower()}.svg",
                media_suggestion=None
            )
            skills.append(skill_spec)
        
        logger.info(f"Generated {len(skills)} thinking skills for {scaffold_type} (difficulty {difficulty}): {[(s.name, s.color) for s in skills]}")
        return skills
    
    def _infer_color_from_scaffold_and_difficulty(self, scaffold_type: str, difficulty: float, position: int, total_steps: int) -> str:
        """Infer cognitive color based on scaffold type, difficulty, and position in lesson"""
        
        # For very low difficulty lessons, start with Green regardless of scaffold
        if difficulty <= 0.25 and position == 0:
            return "Green"
        
        # For high difficulty lessons, may use Orange for communication focus
        if difficulty >= 0.8 and scaffold_type == "sayit":
            return "Orange"
        
        # Default mapping based on scaffold type and cognitive progression
        base_colors = {
            "mapit": "Blue",      # Organizing ideas
            "sayit": "Yellow",    # Critical thinking/communication
            "buildit": "Red"      # Applying knowledge
        }
        
        # Adjust based on lesson position for cognitive progression
        base_color = base_colors.get(scaffold_type, "Blue")
        
        # Early in lesson and low difficulty - shift toward foundational
        if position == 0 and difficulty <= 0.4:
            color_progression = {"Blue": "Green", "Yellow": "Blue", "Red": "Yellow"}
            return color_progression.get(base_color, base_color)
        
        # Late in lesson and high difficulty - shift toward application
        if position >= total_steps - 1 and difficulty >= 0.7:
            color_progression = {"Blue": "Yellow", "Yellow": "Red", "Green": "Blue"}
            return color_progression.get(base_color, base_color)
        
        return base_color
    
    def _generate_example_question(self, skill_name: str, scaffold_type: str) -> str:
        """Generate example question based on skill and scaffold"""
        question_templates = {
            "mapit": {
                "categorise": "How can we group these items?",
                "compare": "What are the similarities and differences?",
                "sequence": "What is the correct order for these steps?",
                "connect": "How are these concepts related?",
                "identify": "What can you recognize in this information?"
            },
            "sayit": {
                "explain": "Can you explain what's happening here?",
                "validate": "What evidence supports this claim?",
                "exemplify": "Can you give an example of this concept?",
                "elaborate": "Can you add more detail to this idea?",
                "target_vocabulary": "How would you use these key terms?"
            },
            "buildit": {
                "hypothesise": "What do you predict will happen?",
                "judge": "Which option do you think is best and why?",
                "combine": "How can we merge these ideas?",
                "imagine": "What if we tried a different approach?",
                "integrate": "How can we bring these concepts together?"
            }
        }
        
        templates = question_templates.get(scaffold_type, {})
        return templates.get(skill_name.lower(), f"How can we use {skill_name} thinking here?")
    
    def _generate_description_for_skill(self, skill_name: str, scaffold_type: str) -> str:
        """Generate appropriate description for skill"""
        descriptions = {
            # Green skills (foundational)
            "identify": "Recognize and point out specific elements or features",
            "retrieve": "Remember and recall information from memory",
            "recognize": "Notice and identify familiar patterns or objects", 
            "find": "Locate and discover specific items or information",
            "point out": "Show and indicate particular details",
            "name": "Say the names of objects, people, or concepts",
            "list": "Make a simple list of items or ideas",
            "recall": "Remember and share what was learned before",
            "state": "Say clearly and simply what you know",
            "describe": "Tell about something using simple words",
            "sort": "Put items into different groups",
            "match": "Find things that go together or are the same",
            "group": "Put similar items together",
            "collect": "Gather items that belong together",
            "arrange": "Put items in a helpful order",
            
            # Standard skills
            "categorise": "Sort items into groups based on shared characteristics",
            "compare": "Identify similarities and differences between concepts", 
            "sequence": "Arrange items in logical or chronological order",
            "rank": "Order items by importance, value, or preference",
            "connect": "Identify relationships and links between ideas",
            "explain": "Communicate understanding clearly with supporting reasons",
            "validate": "Provide evidence to support claims or ideas",
            "exemplify": "Give specific examples to illustrate concepts",
            "target vocabulary": "Use academic language accurately in context",
            "elaborate": "Add detail and depth to ideas and explanations",
            "hypothesise": "Make predictions based on evidence and reasoning",
            "judge": "Evaluate options and make justified decisions",
            "combine": "Merge different ideas or elements into something new",
            "imagine": "Create new and innovative solutions or ideas",
            "integrate": "Bring together concepts from different areas",
            
            # Advanced skills
            "analyze": "Break down complex ideas into smaller parts",
            "synthesize": "Combine different elements to create new understanding",
            "evaluate": "Assess the value or quality of ideas using criteria",
            "argue": "Present a case with evidence and logical reasoning",
            "defend": "Support ideas with strong evidence and reasoning",
            "critique": "Examine strengths and weaknesses thoughtfully",
            "justify": "Explain the reasons behind decisions or beliefs",
            "design": "Plan and create solutions to complex problems",
            "create": "Develop original ideas or products",
            "innovate": "Develop new and creative approaches",
            "construct": "Build understanding or solutions systematically",
            "engineer": "Design and build solutions using systematic thinking"
        }
        
        return descriptions.get(skill_name.lower(), f"Apply {skill_name} thinking to develop understanding")
    
    async def _select_with_rag_progression(
        self,
        available_skills: Dict[str, List[SkillSpec]],
        step_count: int,
        difficulty: float,
        preferred_blocks: Optional[List[str]],
        subject: str,
        topic: str
    ) -> List[SkillSpec]:
        """Select skills with cognitive progression using RAG-discovered skills"""
        
        selected_skills = []
        
        # Define preferred progression for different contexts (only used if no preferred_blocks)
        if difficulty <= 0.3:
            default_progression = ["mapit", "sayit"]  # Start simple
        elif difficulty <= 0.7:
            default_progression = ["mapit", "sayit", "buildit"]  # Balanced
        else:
            default_progression = ["sayit", "buildit", "mapit"]  # Advanced thinking first
        
        for i in range(step_count):
            # Determine target scaffold type
            if preferred_blocks and i < len(preferred_blocks):
                # Convert preferred block names to lowercase scaffold format
                block_name = preferred_blocks[i]
                if block_name == "MapIt":
                    target_scaffold = "mapit"
                elif block_name == "SayIt":
                    target_scaffold = "sayit"
                elif block_name == "BuildIt":
                    target_scaffold = "buildit"
                else:
                    # Fallback for any other format
                    target_scaffold = block_name.lower().replace("it", "")
                
                logger.info(f"Using preferred block {block_name} -> {target_scaffold}")
                
            elif i < len(default_progression):
                target_scaffold = default_progression[i]
                logger.info(f"Using default progression: {target_scaffold}")
            else:
                # Cycle through available scaffolds
                available_scaffolds = list(available_skills.keys())
                target_scaffold = available_scaffolds[i % len(available_scaffolds)]
                logger.info(f"Cycling through available: {target_scaffold}")
            
            # Select skill from target scaffold
            skill = self._select_skill_from_scaffold_simple(
                available_skills=available_skills,
                target_scaffold=target_scaffold,
                already_selected=[s.name for s in selected_skills]
            )
            
            if skill:
                selected_skills.append(skill)
                logger.info(f"Selected skill: {skill.name} ({skill.block_type})")
            else:
                logger.warning(f"No skill found for scaffold: {target_scaffold}")
            
        return selected_skills
    
    def _select_skill_from_scaffold_simple(
        self,
        available_skills: Dict[str, List[SkillSpec]],
        target_scaffold: str,
        already_selected: List[str]
    ) -> Optional[SkillSpec]:
        """Select a skill from target scaffold type without additional API calls"""
        
        scaffold_skills = available_skills.get(target_scaffold, [])
        
        # Filter out already selected skills
        available_for_selection = [
            skill for skill in scaffold_skills 
            if skill.name not in already_selected
        ]
        
        if not available_for_selection:
            # Try other scaffolds as fallback
            for scaffold, skills in available_skills.items():
                if scaffold != target_scaffold:
                    available_for_selection = [
                        skill for skill in skills 
                        if skill.name not in already_selected
                    ]
                    if available_for_selection:
                        break
        
        if not available_for_selection:
            return None
        
        # Simple selection - just pick randomly from available skills
        return random.choice(available_for_selection)
    
    async def _fallback_skill_selection(
        self, 
        difficulty: float, 
        step_count: int, 
        preferred_blocks: Optional[List[str]]
    ) -> List[SkillSpec]:
        """Fallback to basic skill selection if RAG fails"""
        logger.info("Using fallback skill selection")
        
        # Import static selector as fallback
        from app.core.skills.selector import skill_selector
        return skill_selector.select_skills_for_lesson(
            difficulty=difficulty,
            step_count=step_count,
            preferred_blocks=preferred_blocks
        )
        
# Global instance
rag_enhanced_skill_selector = RAGEnhancedSkillSelector()