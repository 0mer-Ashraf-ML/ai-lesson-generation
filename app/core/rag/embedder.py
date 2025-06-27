import openai
from typing import List, Dict, Any
from app.config import settings
from app.utils.exceptions import EmbeddingError
from app.utils.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger(__name__)


class TextEmbedder:
    """Handles text embedding generation using OpenAI"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"  # Cost-effective embedding model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        try:
            if not text or not text.strip():
                raise EmbeddingError("Empty text provided for embedding")
            
            # Clean and truncate text if necessary
            cleaned_text = self._clean_text(text)
            
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_text
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(
                "Text embedded successfully",
                text_length=len(text),
                embedding_dimension=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            logger.error("Error generating embedding", error=str(e), text_preview=text[:100])
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        try:
            if not texts:
                return []
            
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts if text and text.strip()]
            
            if not cleaned_texts:
                return []
            
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_texts
            )
            
            embeddings = [data.embedding for data in response.data]
            
            logger.info(
                "Batch embeddings generated successfully",
                batch_size=len(texts),
                embedding_dimension=len(embeddings[0]) if embeddings else 0
            )
            
            return embeddings
            
        except Exception as e:
            logger.error("Error generating batch embeddings", error=str(e), batch_size=len(texts))
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Truncate if too long (embedding models have token limits)
        max_chars = 8000  # Conservative limit for text-embedding-3-small
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
            logger.warning("Text truncated for embedding", original_length=len(text))
        
        return cleaned
    
    def create_query_embedding(self, topic: str, subject: str, grade: str, curriculum: str) -> str:
        """Create a search query string optimized for curriculum retrieval"""
        query_parts = [topic, subject, grade, curriculum]
        query = " ".join(part for part in query_parts if part)
        return query


# Global instance
text_embedder = TextEmbedder()