from typing import List, Optional, Dict, Tuple,Any
import uuid
import random
import time
from datetime import datetime
from app.models.requests import LessonRequest
from app.models.responses import LessonResponse, LessonMetadata
from app.models.lesson import LessonPlan, GenerationContext
from app.core.skills.rag_enhanced_selector import rag_enhanced_skill_selector
from app.core.generation.enhanced_block_generator import enhanced_block_generator
from app.core.rag.context_builder import rag_context_builder
from app.services.storage_service import storage_service
from app.utils.exceptions import SkillSelectionError, LLMGenerationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TimeAwareLessonService:
    """Advanced lesson service with time awareness and intelligent scaffolding"""
    
    def __init__(self):
        self.skill_selector = rag_enhanced_skill_selector
        self.block_generator = enhanced_block_generator
        self.rag_builder = rag_context_builder
        self.storage_service = storage_service
    
    async def generate_adaptive_lesson(
        self,
        request: LessonRequest,
        user_id: Optional[str] = None
    ) -> LessonResponse:
        """
        Generate a lesson with intelligent time and scaffolding management
        
        Args:
            request: Enhanced lesson request with time constraints
            user_id: Optional user ID for saving
            
        Returns:
            Complete lesson response with adaptive features
        """
        try:
            lesson_id = str(int(time.time() * 1000))
            
            logger.info(
                "Starting time-aware lesson generation",
                lesson_id=lesson_id,
                topic=request.topic,
                available_time=request.available_time_minutes,
                time_flexibility=request.time_flexibility,
                prefer_variety=request.prefer_variety
            )
            
            # Step 1: Time-aware scaffold sequence planning
            preferred_scaffolds = await self._plan_scaffold_sequence(
                request=request
            )
            
            # Step 2: Select skills using RAG system
            selected_skills = await self.skill_selector.select_skills_for_lesson(
                difficulty=request.difficulty,
                step_count=request.step_count,
                subject=request.subject,
                topic=request.topic,
                preferred_blocks=preferred_scaffolds
            )
            
            # Step 3: Build enhanced generation context
            generation_context = await self.rag_builder.build_lesson_context(
                topic=request.topic,
                subject=request.subject,
                grade=request.grade,
                curriculum=request.curriculum,
                skills=selected_skills
            )
            generation_context.difficulty = request.difficulty
            
            # Step 4: Generate adaptive blocks with intelligent scaffolding
            lesson_blocks, scaffolding_summary = await self.block_generator.generate_adaptive_lesson_blocks(
                skills=selected_skills,
                context=generation_context,
                available_time_minutes=request.available_time_minutes,
                time_flexibility=request.time_flexibility
            )
                     
            # Step 6: Create enhanced metadata
            lesson_metadata = self._create_time_aware_metadata(
                skills=selected_skills,
                difficulty=request.difficulty,
                scaffolding_summary=scaffolding_summary,
                available_time=request.available_time_minutes,
                adaptations_made=self._identify_adaptations(scaffolding_summary, request)
            )
            
            # Step 7: Save lesson if user provided
            if user_id:
                await self._save_adaptive_lesson_plan(
                    lesson_id=lesson_id,
                    request=request,
                    blocks=lesson_blocks,
                    metadata=lesson_metadata,
                    user_id=user_id
                )
            
            # Step 8: Create response
            lesson_response = LessonResponse(
                lesson_id=lesson_id,
                topic=request.topic,
                grade=request.grade,
                subject=request.subject,
                curriculum=request.curriculum,
                difficulty=request.difficulty,
                blocks=lesson_blocks,
                metadata=lesson_metadata
            )
            
            logger.info(
                "Time-aware lesson generation completed",
                lesson_id=lesson_id,
                blocks_generated=len(lesson_blocks),
                full_scaffolds=scaffolding_summary["full_scaffolds"],
                simple_prompts=scaffolding_summary["simple_prompts"],
                total_time=scaffolding_summary["total_time_estimate"]
            )
            
            return lesson_response
            
        except Exception as e:
            logger.error("Error in adaptive lesson generation", error=str(e))
            raise
    
    async def _plan_scaffold_sequence(self, request: LessonRequest) -> List[str]:
        """Plan scaffold sequence considering time and variety preferences"""
        
        # If teacher specified preferences, respect them
        if request.preferred_blocks:
            return [block.value for block in request.preferred_blocks]
        
        # Otherwise, generate intelligent sequence
        return self._generate_time_aware_sequence(
            step_count=request.step_count,
            difficulty=request.difficulty,
            available_time=request.available_time_minutes,
            time_flexibility=request.time_flexibility,
            prefer_variety=request.prefer_variety
        )
    
    def _generate_time_aware_sequence(
        self,
        step_count: int,
        difficulty: float,
        available_time: Optional[int] = None,
        time_flexibility: str = "moderate",
        prefer_variety: bool = True
    ) -> List[str]:
        """Generate scaffold sequence considering time constraints"""
        
        # Time estimates per scaffold type
        time_estimates = {"MapIt": 15, "SayIt": 10, "BuildIt": 20}
        
        if available_time:
            avg_time_per_step = available_time / step_count
            
            # Very tight time - favor discussion
            if avg_time_per_step < 8 or time_flexibility == "strict":
                return ["SayIt"] * step_count
            
            # Moderate time - balanced approach
            elif avg_time_per_step < 12:
                sequence = []
                for i in range(step_count):
                    if i == 0:
                        sequence.append("MapIt")  # Start with organization
                    else:
                        sequence.append("SayIt")  # Discussion for rest
                return sequence
            
            # Sufficient time but still constrained
            elif avg_time_per_step < 18:
                return self._generate_moderate_time_sequence(step_count, difficulty, prefer_variety)
        
        # Ample time or no constraints - full variety
        return self._generate_varied_scaffold_sequence(step_count, difficulty, prefer_variety)
    
    def _generate_moderate_time_sequence(self, step_count: int, difficulty: float, prefer_variety: bool) -> List[str]:
        """Generate sequence for moderate time constraints"""
        
        sequence = []
        
        # Always start with MapIt for organization
        if step_count >= 1:
            sequence.append("MapIt")
        
        # Add SayIt for discussion
        if step_count >= 2:
            sequence.append("SayIt")
        
        # Selectively add BuildIt for higher difficulty
        if step_count >= 3 and difficulty > 0.6:
            sequence.append("BuildIt")
        elif step_count >= 3:
            sequence.append("MapIt")  # Safer alternative
        
        # Fill remaining with alternating MapIt/SayIt
        while len(sequence) < step_count:
            last_type = sequence[-1]
            if last_type == "MapIt":
                sequence.append("SayIt")
            else:
                sequence.append("MapIt")
        
        return sequence
    
    def _generate_varied_scaffold_sequence(self, step_count: int, difficulty: float, prefer_variety: bool) -> List[str]:
        """Generate varied sequence when time allows"""
        
        sequence = []
        
        # Ensure we include each type at least once if possible
        base_types = ["MapIt", "SayIt"]
        if difficulty > 0.5 and step_count >= 3:
            base_types.append("BuildIt")
        
        # Add base types first
        for i, scaffold_type in enumerate(base_types):
            if i < step_count:
                sequence.append(scaffold_type)
        
        # Fill remaining slots with variety
        while len(sequence) < step_count:
            if prefer_variety:
                # Avoid three consecutive of same type
                if len(sequence) >= 2 and sequence[-1] == sequence[-2]:
                    available_types = [t for t in base_types if t != sequence[-1]]
                    sequence.append(random.choice(available_types))
                else:
                    # Weighted selection based on difficulty
                    weights = self._get_scaffold_weights(difficulty)
                    scaffold_type = random.choices(
                        list(weights.keys()),
                        weights=list(weights.values())
                    )[0]
                    sequence.append(scaffold_type)
            else:
                # Simple alternating pattern
                last_type = sequence[-1]
                if last_type == "MapIt":
                    sequence.append("SayIt")
                elif last_type == "SayIt":
                    sequence.append("BuildIt" if difficulty > 0.5 else "MapIt")
                else:
                    sequence.append("MapIt")
        
        return sequence
    
    def _get_scaffold_weights(self, difficulty: float) -> Dict[str, float]:
        """Get weighted preferences for scaffold types based on difficulty"""
        
        if difficulty <= 0.3:
            return {"MapIt": 0.5, "SayIt": 0.4, "BuildIt": 0.1}
        elif difficulty <= 0.5:
            return {"MapIt": 0.4, "SayIt": 0.4, "BuildIt": 0.2}
        elif difficulty <= 0.7:
            return {"MapIt": 0.3, "SayIt": 0.4, "BuildIt": 0.3}
        else:
            return {"MapIt": 0.2, "SayIt": 0.3, "BuildIt": 0.5}
    
    def _create_time_aware_metadata(
        self,
        skills: List,
        difficulty: float,
        scaffolding_summary: Dict[str, Any],
        available_time: Optional[int] = None,
        adaptations_made: List[str] = None
    ) -> LessonMetadata:
        """Create enhanced metadata with time and scaffolding info"""
        
        skills_used = [skill.name for skill in skills]
        cognitive_progression = [skill.color for skill in skills]
        
        # Calculate time breakdown
        time_breakdown = {
            "full_scaffolds": scaffolding_summary["full_scaffolds"] * 15,  # Avg 15 min
            "simple_prompts": scaffolding_summary["simple_prompts"] * 5,   # Avg 5 min
            "total_estimated": scaffolding_summary["total_time_estimate"]
        }
        
        # Enhanced difficulty level with context
        difficulty_level = self._get_enhanced_difficulty_level(
            difficulty, 
            scaffolding_summary,
            available_time
        )
        
        return LessonMetadata(
            skills_used=skills_used,
            cognitive_progression=cognitive_progression,
            estimated_duration=f"{scaffolding_summary['total_time_estimate']} minutes",
            difficulty_level=difficulty_level,
            scaffolding_summary=scaffolding_summary,
            time_breakdown=time_breakdown,
            adaptations_made=adaptations_made or []
        )
    
    def _get_enhanced_difficulty_level(
        self, 
        difficulty: float, 
        scaffolding_summary: Dict[str, Any], 
        available_time: Optional[int]
    ) -> str:
        """Get enhanced difficulty level description"""
        
        base_levels = {
            (0.0, 0.3): "Foundational",
            (0.3, 0.5): "Developing", 
            (0.5, 0.7): "Proficient",
            (0.7, 1.0): "Advanced"
        }
        
        base_level = "Developing"  # default
        for (low, high), label in base_levels.items():
            if low <= difficulty <= high:
                base_level = label
                break
        
        # Add contextual information
        modifiers = []
        
        if scaffolding_summary["scaffold_ratio"] < 0.5:
            modifiers.append("Discussion-Focused")
        elif scaffolding_summary["scaffold_ratio"] > 0.8:
            modifiers.append("Activity-Rich")
        
        if available_time and available_time < 30:
            modifiers.append("Time-Efficient")
        elif available_time and available_time > 60:
            modifiers.append("Extended")
        
        if modifiers:
            return f"{base_level} ({', '.join(modifiers)})"
        else:
            return base_level
    
    def _identify_adaptations(
        self, 
        scaffolding_summary: Dict[str, Any], 
        request: LessonRequest
    ) -> List[str]:
        """Identify what adaptations were made for time/complexity"""
        
        adaptations = []
        
        if scaffolding_summary["simple_prompts"] > 0:
            adaptations.append(f"Converted {scaffolding_summary['simple_prompts']} activities to discussion prompts")
        
        if request.available_time_minutes:
            if scaffolding_summary["total_time_estimate"] <= request.available_time_minutes:
                adaptations.append(f"Optimized for {request.available_time_minutes}-minute time slot")
            else:
                adaptations.append("Time-efficient alternatives selected")
        
        if request.time_flexibility == "strict":
            adaptations.append("Strict time constraints applied")
        
        if scaffolding_summary["scaffold_ratio"] < 0.3:
            adaptations.append("Emphasized discussion over complex activities")
        
        return adaptations
    
    async def _save_adaptive_lesson_plan(
        self,
        lesson_id: str,
        request: LessonRequest,
        blocks: List,
        metadata: LessonMetadata,
        user_id: str
    ):
        """Save adaptive lesson plan with enhanced metadata"""
        
        lesson_plan = LessonPlan(
            id=lesson_id,
            user_id=user_id,
            title=f"{request.topic} - {request.grade} {request.subject} (Time-Aware)",
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            curriculum=request.curriculum,
            difficulty=request.difficulty,
            blocks=[block.dict() for block in blocks],
            metadata={
                **metadata.dict(),
                "generation_type": "time_aware",
                "time_constraints": {
                    "available_time": request.available_time_minutes,
                    "time_flexibility": request.time_flexibility,
                    "prefer_variety": request.prefer_variety
                },
                "adaptive_features": True
            }
        )
        
        await self.storage_service.save_lesson(lesson_plan)
    
    async def get_lesson(self, lesson_id: str, user_id: Optional[str] = None) -> Optional[LessonResponse]:
        """Get lesson with enhanced features"""
        try:
            lesson_plan = await self.storage_service.get_lesson(lesson_id)
            
            if not lesson_plan:
                return None
            
            if user_id and lesson_plan.user_id != user_id:
                logger.warning("User attempted to access lesson they don't own")
                return None
            
            return self._lesson_plan_to_response(lesson_plan)
            
        except Exception as e:
            logger.error("Error retrieving lesson", error=str(e))
            raise
    
    async def get_user_lessons(self, user_id: str, limit: int = 50) -> List[LessonResponse]:
        """Get user lessons with enhanced metadata"""
        try:
            lesson_plans = await self.storage_service.get_user_lessons(user_id, limit)
            
            lesson_responses = []
            for plan in lesson_plans:
                response = self._lesson_plan_to_response(plan)
                lesson_responses.append(response)
            
            return lesson_responses
            
        except Exception as e:
            logger.error("Error retrieving user lessons", error=str(e))
            raise
    
    def _lesson_plan_to_response(self, lesson_plan: LessonPlan) -> LessonResponse:
        """Convert lesson plan to response with enhanced features"""
        
        from app.models.responses import LessonBlock
        
        # Convert blocks
        blocks = []
        for block_data in lesson_plan.blocks:
            # Handle both old and new block formats
            if isinstance(block_data, dict):
                blocks.append(LessonBlock(**block_data))
            else:
                blocks.append(block_data)
        
        # Convert metadata
        metadata = LessonMetadata(**lesson_plan.metadata)
        
        return LessonResponse(
            lesson_id=lesson_plan.id,
            topic=lesson_plan.topic,
            grade=lesson_plan.grade,
            subject=lesson_plan.subject,
            curriculum=lesson_plan.curriculum,
            difficulty=lesson_plan.difficulty,
            blocks=blocks,
            metadata=metadata,
            generated_at=lesson_plan.created_at
        )
    
    async def generate_lesson_sequence(
        self,
        base_request: LessonRequest,
        sequence_length: int,
        user_id: Optional[str] = None
    ) -> List[LessonResponse]:
        """Generate a sequence of related lessons with cross-lesson variety"""
        
        try:
            logger.info(
                "Generating lesson sequence",
                topic=base_request.topic,
                sequence_length=sequence_length
            )
            
            lessons = []
            used_scaffolds = []
            
            for i in range(sequence_length):
                # Modify request for sequence variety
                sequence_request = self._create_sequence_request(
                    base_request, i, sequence_length, used_scaffolds
                )
                
                # Generate lesson
                lesson = await self.generate_adaptive_lesson(sequence_request, user_id)
                lessons.append(lesson)
                
                # Track scaffolds used for variety
                lesson_scaffolds = [block.type for block in lesson.blocks]
                used_scaffolds.extend(lesson_scaffolds)
            
            logger.info(f"Generated sequence of {len(lessons)} lessons")
            return lessons
            
        except Exception as e:
            logger.error("Error generating lesson sequence", error=str(e))
            raise
    
    def _create_sequence_request(
        self,
        base_request: LessonRequest,
        position: int,
        total_lessons: int,
        used_scaffolds: List[str]
    ) -> LessonRequest:
        """Create modified request for sequence position"""
        
        # Create copy of base request
        sequence_request = base_request.copy()
        
        # Adjust difficulty progression
        if total_lessons > 1:
            difficulty_progression = position / (total_lessons - 1)
            sequence_request.difficulty = (
                base_request.difficulty * 0.7 + 
                difficulty_progression * 0.3
            )
        
        # Ensure variety across sequence
        if position > 0:
            # Count recent scaffold usage
            recent_scaffolds = used_scaffolds[-6:]  # Last 6 blocks
            scaffold_counts = {
                "MapIt": recent_scaffolds.count("MapIt"),
                "SayIt": recent_scaffolds.count("SayIt"), 
                "BuildIt": recent_scaffolds.count("BuildIt")
            }
            
            # Prefer less-used scaffolds
            min_count = min(scaffold_counts.values())
            preferred = [k for k, v in scaffold_counts.items() if v == min_count]
            
            if len(preferred) < base_request.step_count:
                # Add variety
                all_types = ["MapIt", "SayIt", "BuildIt"]
                for scaffold_type in all_types:
                    if scaffold_type not in preferred and len(preferred) < base_request.step_count:
                        preferred.append(scaffold_type)
            
            # Set preferred blocks for variety
            sequence_request.preferred_blocks = preferred[:base_request.step_count]
        
        return sequence_request


# Global instance
time_aware_lesson_service = TimeAwareLessonService()