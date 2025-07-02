from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SkillColor(str, Enum):
    GREEN = "Green"
    BLUE = "Blue"
    YELLOW = "Yellow"
    ORANGE = "Orange"
    RED = "Red"


class BlockType(str, Enum):
    MAP_IT = "MapIt"
    SAY_IT = "SayIt"
    BUILD_IT = "BuildIt"
    PROMPT = "Prompt"  # Simple prompt instead of full scaffold


class SkillMetadata(BaseModel):
    name: str
    color: SkillColor
    icon_url: str
    category: str


class ResourceLink(BaseModel):
    """Link to a supporting resource"""
    type: str  # "pdf", "video", "image"
    name: str
    description: Optional[str] = None
    url: str


class LessonBlock(BaseModel):
    id: str
    type: BlockType
    title: str
    description: str
    steps: List[str]
    skill: SkillMetadata
    supporting_question: str
    complexity_level: str
    complexity_display_name: str
    media: Optional[List[str]] = []
    sentence_starters: Optional[List[str]] = []
    materials: Optional[List[str]] = []
    target_words: Optional[List[str]] = []
    criteria: Optional[List[str]] = []
    resources: Optional[List[ResourceLink]] = []
    
    # Fields for prompt-type blocks
    interaction_type: Optional[str] = None  # "think_pair_share", "whole_class", etc.
    follow_up_questions: Optional[List[str]] = []
    success_indicators: Optional[List[str]] = []
    

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class LessonMetadata(BaseModel):
    skills_used: List[str]
    cognitive_progression: List[str]
    estimated_duration: str
    difficulty_level: str
    complexity_levels: Optional[List[str]] = []  # Make this field optional with a default empty list


class LessonResponse(BaseModel):
    lesson_id: str
    topic: str
    grade: str
    subject: str
    curriculum: str
    difficulty: float
    blocks: List[LessonBlock]
    metadata: LessonMetadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)