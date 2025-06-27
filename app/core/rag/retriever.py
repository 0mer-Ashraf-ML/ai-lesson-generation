from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from app.config import settings
from app.core.rag.embedder import text_embedder
from app.utils.exceptions import RAGRetrievalError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CurriculumRetriever:
    def __init__(self):
        self._pinecone = Pinecone(api_key=settings.pinecone_api_key)
        self._index = None
        self._initialize_pinecone()

    def _initialize_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            indexes = self._pinecone.list_indexes().names()

            if settings.pinecone_index_name not in indexes:
                logger.warning(
                    "Pinecone index not found - will need to be created",
                    index_name=settings.pinecone_index_name
                )
            else:
                self._index = self._pinecone.Index(settings.pinecone_index_name)
                logger.info("Pinecone index connected successfully")

        except Exception as e:
            logger.error("Failed to initialize Pinecone", error=str(e))
    
    async def retrieve_context(
        self,
        topic: str,
        subject: str,
        grade: str,
        curriculum: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant curriculum context for a lesson topic
        
        Args:
            topic: Lesson topic
            subject: Subject area
            grade: Grade level
            curriculum: Curriculum standard
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            List of relevant curriculum chunks with metadata
        """
        try:
            if not self._index:
                logger.warning("Pinecone index not available - returning empty context")
                return []
            
            # Create search query
            query_text = text_embedder.create_query_embedding(topic, subject, grade, curriculum)
            
            # Generate query embedding
            query_embedding = await text_embedder.embed_text(query_text)
            
            # Build metadata filter
            metadata_filter = self._build_metadata_filter(subject, grade, curriculum)
            
            # Search in Pinecone
            search_results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                filter=metadata_filter
            )
            
            # Process results
            context_chunks = []
            for match in search_results.matches:
                chunk = {
                    'id': match.id,
                    'score': match.score,
                    'content': match.metadata.get('content', ''),
                    'source': match.metadata.get('source', ''),
                    'subject': match.metadata.get('subject', ''),
                    'grade': match.metadata.get('grade', ''),
                    'curriculum': match.metadata.get('curriculum', ''),
                    'chunk_type': match.metadata.get('chunk_type', '')
                }
                context_chunks.append(chunk)
            
            logger.info(
                "Retrieved curriculum context",
                query=query_text,
                results_count=len(context_chunks),
                avg_score=sum(c['score'] for c in context_chunks) / len(context_chunks) if context_chunks else 0
            )
            
            return context_chunks
            
        except Exception as e:
            logger.error("Error retrieving curriculum context", error=str(e))
            # Don't raise - allow graceful degradation with empty context
            return []
    
    def _build_metadata_filter(self, subject: str, grade: str, curriculum: str) -> Dict[str, Any]:
        """Build Pinecone metadata filter"""
        filter_conditions = {}
        
        if subject:
            filter_conditions['subject'] = {'$eq': subject}
        
        if grade:
            # Handle different grade formats
            grade_variations = [grade]
            if 'Year' in grade:
                # Add numeric equivalent (e.g., "Year 4" -> "Grade 4")
                numeric = grade.replace('Year', 'Grade')
                grade_variations.append(numeric)
            elif 'Grade' in grade:
                # Add Year equivalent
                year = grade.replace('Grade', 'Year')
                grade_variations.append(year)
            
            filter_conditions['grade'] = {'$in': grade_variations}
        
        if curriculum:
            filter_conditions['curriculum'] = {'$eq': curriculum}
        
        return filter_conditions
    
    async def retrieve_by_skill(
        self,
        skill_name: str,
        block_type: str,
        subject: str = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve context specific to a thinking skill and block type
        
        Args:
            skill_name: Name of the thinking skill (e.g., "Compare", "Categorise")
            block_type: Type of block (MapIt, SayIt, BuildIt)
            subject: Optional subject filter
            top_k: Number of results to retrieve
            
        Returns:
            List of relevant examples and resources
        """
        try:
            if not self._index:
                return []
            
            # Create skill-specific query
            query_text = f"{skill_name} {block_type} teaching strategy example"
            if subject:
                query_text += f" {subject}"
            
            query_embedding = await text_embedder.embed_text(query_text)
            
            # Build filter for instructional resources
            metadata_filter = {
                'chunk_type': {'$eq': 'instructional_strategy'}
            }
            if subject:
                metadata_filter['subject'] = {'$eq': subject}
            
            search_results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                filter=metadata_filter
            )
            
            # Process results
            strategy_examples = []
            for match in search_results.matches:
                example = {
                    'id': match.id,
                    'score': match.score,
                    'content': match.metadata.get('content', ''),
                    'strategy_type': match.metadata.get('strategy_type', ''),
                    'skill': match.metadata.get('skill', ''),
                    'example_activity': match.metadata.get('example_activity', '')
                }
                strategy_examples.append(example)
            
            logger.debug(
                "Retrieved skill-specific context",
                skill=skill_name,
                block_type=block_type,
                results_count=len(strategy_examples)
            )
            
            return strategy_examples
            
        except Exception as e:
            logger.error("Error retrieving skill context", error=str(e))
            return []
    
    def health_check(self) -> bool:
        """Check if Pinecone connection is healthy"""
        try:
            if not self._index:
                return False
            
            # Try a simple query
            stats = self._index.describe_index_stats()
            return stats is not None
            
        except Exception as e:
            logger.error("Pinecone health check failed", error=str(e))
            return False


# Global instance
curriculum_retriever = CurriculumRetriever()