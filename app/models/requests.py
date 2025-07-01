from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum


class BlockType(str, Enum):
    MAP_IT = "MapIt"
    SAY_IT = "SayIt"
    BUILD_IT = "BuildIt"


class LessonRequest(BaseModel):
    grade: str = Field(..., description="Grade level (e.g., 'Year 4', 'Grade 5')")
    curriculum: str = Field(..., description="Curriculum standard (e.g., 'UK KS2', 'NGSS')")
    subject: str = Field(..., description="Subject area (e.g., 'Science', 'Mathematics')")
    topic: str = Field(..., description="Specific topic for the lesson")
    difficulty: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0, 
        description="Difficulty level from 0.0 (easy) to 1.0 (hard)"
    )
    step_count: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Number of blocks to generate"
    )
    preferred_blocks: Optional[List[BlockType]] = Field(
        default=None,
        description="Optional preference for block types"
    )
    
    # NEW: Time-aware planning fields
    available_time_minutes: Optional[int] = Field(
        default=None,
        ge=10,
        le=120,
        description="Available lesson time in minutes (affects complexity and scaffolding decisions)"
    )
    prefer_variety: bool = Field(
        default=True,
        description="Whether to prioritize variety over time efficiency"
    )
    time_flexibility: str = Field(
        default="moderate",
        description="How flexible the timing is: 'strict', 'moderate', or 'flexible'"
    )
    
    @validator('time_flexibility')
    def validate_time_flexibility(cls, v):
        if v not in ['strict', 'moderate', 'flexible']:
            raise ValueError('time_flexibility must be "strict", "moderate", or "flexible"')
        return v
    
    @validator('available_time_minutes')
    def validate_time_vs_steps(cls, v, values):
        if v is not None and 'step_count' in values:
            min_time_needed = values['step_count'] * 5  # Minimum 5 minutes per step
            if v < min_time_needed:
                raise ValueError(f'Available time ({v} min) is too short for {values["step_count"]} steps. Minimum needed: {min_time_needed} min')
        return v


class SequenceRequest(BaseModel):
    """Request for generating a sequence of related lessons"""
    base_request: LessonRequest
    sequence_length: int = Field(ge=2, le=10, description="Number of lessons in sequence")
    sequence_focus: str = Field(
        default="progression",
        description="Focus of sequence: 'progression', 'variety', or 'depth'"
    )
    cross_lesson_variety: bool = Field(
        default=True,
        description="Ensure variety across lessons in the sequence"
    )