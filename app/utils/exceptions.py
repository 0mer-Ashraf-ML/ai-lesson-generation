class StructuralLearningException(Exception):
    """Base exception for Structural Learning application"""
    pass


class ValidationError(StructuralLearningException):
    """Raised when validation fails"""
    pass


class SkillSelectionError(StructuralLearningException):
    """Raised when skill selection fails"""
    pass


class LLMGenerationError(StructuralLearningException):
    """Raised when LLM generation fails"""
    pass


class RAGRetrievalError(StructuralLearningException):
    """Raised when RAG retrieval fails"""
    pass


class DatabaseError(StructuralLearningException):
    """Raised when database operations fail"""
    pass


class EmbeddingError(StructuralLearningException):
    """Raised when embedding generation fails"""
    pass