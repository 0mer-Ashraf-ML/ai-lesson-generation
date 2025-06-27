from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4


class SkillSpec(BaseModel):
    """Specification for a thinking skill"""
    name: str
    color: str
    block_type: str
    example_question: str
    description: str
    icon_url: str
    media_suggestion: Optional[str] = None


class BlockSpec(BaseModel):
    """Specification for generating a lesson block"""
    skill: SkillSpec
    sequence_order: int
    context: Dict[str, Any]


class LessonPlan(BaseModel):
    """Internal lesson plan model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    title: str
    topic: str
    grade: str
    subject: str
    curriculum: str
    difficulty: float
    blocks: List[Dict[str, Any]]  # Will contain LessonBlock data
    metadata: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GenerationContext(BaseModel):
    """Context for lesson generation"""
    topic: str
    grade: str
    subject: str
    curriculum: str
    difficulty: float
    curriculum_context: Optional[str] = None  # RAG context
    user_preferences: Optional[Dict[str, Any]] = None