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
        ge=2, 
        le=5, 
        description="Number of blocks to generate"
    )
    preferred_blocks: Optional[List[BlockType]] = Field(
        default=None,
        description="Optional preference for block types"
    )