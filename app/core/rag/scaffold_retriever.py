from typing import List, Dict, Any, Optional
from app.config import settings
from app.core.rag.embedder import text_embedder
from pinecone import Pinecone
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ScaffoldResourceRetriever:
    """Retrieves scaffold-specific resources (BuildIt, SayIt, MapIt)"""
    
    def __init__(self):
        self._pinecone = Pinecone(api_key=settings.pinecone_api_key)
        self._index = None
        self._initialize_pinecone()
        # Configure your resource base URL
        self._resource_base_url = "http://localhost:8000/resources"  # Update this with your actual URL
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            indexes = self._pinecone.list_indexes().names()
            if settings.pinecone_index_name in indexes:
                self._index = self._pinecone.Index(settings.pinecone_index_name)
                logger.info("Pinecone index connected for scaffold retrieval")
            else:
                logger.warning(f"Pinecone index '{settings.pinecone_index_name}' not found")
        except Exception as e:
            logger.error("Failed to initialize Pinecone for scaffold retrieval", error=str(e))
    
    def _create_resource_url(self, file_path: str) -> str:
        """Create a URL for accessing a resource file"""
        if not file_path:
            return None
        return f"{self._resource_base_url}/{file_path}"
    
    async def retrieve_scaffold_resources(
        self,
        scaffold_type: str,
        skill_name: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieve scaffold resources (PDFs, images, videos)
        
        Args:
            scaffold_type: "buildit", "sayit", or "mapit"
            skill_name: Optional specific skill to retrieve resources for
            topic: Optional topic to improve relevance
            top_k: Maximum number of PDF resources to retrieve
            
        Returns:
            Dict containing PDFs, image, and video resources
        """
        try:
            if not self._index:
                logger.warning("Pinecone index not available")
                return {"pdfs": [], "image": None, "video": None}
            
            # Normalize inputs
            scaffold_type = scaffold_type.lower().replace("it", "")  # Convert "BuildIt" -> "build"
            
            # Build query text
            query_parts = [f"{scaffold_type} scaffold resource"]
            if skill_name:
                query_parts.append(f"{skill_name} thinking skill")
            if topic:
                query_parts.append(f"for {topic}")
                
            query_text = " ".join(query_parts)
            
            # Generate embedding
            query_embedding = await text_embedder.embed_text(query_text)
            
            # Build filter
            filter_condition = {
                "scaffold_type": {"$eq": scaffold_type},
                "content_type": {"$eq": "pdf"}
            }
            
            if skill_name:
                filter_condition["skill_name"] = {"$eq": skill_name.lower()}
            
            # Search in Pinecone
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                filter=filter_condition
            )
            
            # Process results
            pdf_resources = []
            image_url = None
            video_url = None
            
            for match in results.matches:
                metadata = match.metadata
                
                # Process PDF resource
                pdf_resources.append({
                    "id": match.id,
                    "score": match.score,
                    "name": metadata.get("file_name", "Resource"),
                    "skill": metadata.get("skill_name", ""),
                    "content_preview": metadata.get("content_preview", ""),
                    "url": self._create_resource_url(metadata.get("file_path"))
                })
                
                # Get image and video URLs (from first matching document)
                if not image_url and metadata.get("related_image"):
                    image_url = self._create_resource_url(metadata.get("related_image"))
                
                if not video_url and metadata.get("related_video"):
                    video_url = self._create_resource_url(metadata.get("related_video"))
            
            result = {
                "pdfs": pdf_resources,
                "image": image_url,
                "video": video_url
            }
            
            logger.info(
                "Retrieved scaffold resources",
                scaffold=scaffold_type,
                skill=skill_name,
                pdf_count=len(pdf_resources),
                has_image=image_url is not None,
                has_video=video_url is not None
            )
            
            return result
            
        except Exception as e:
            logger.error("Error retrieving scaffold resources", error=str(e))
            return {"pdfs": [], "image": None, "video": None}
    
    async def retrieve_by_skill(
        self,
        skill_name: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve resources for a specific thinking skill across all scaffold types
        
        Args:
            skill_name: Name of the thinking skill
            top_k: Maximum number of resources to retrieve
            
        Returns:
            List of resources for the skill
        """
        try:
            if not self._index:
                return []
            
            # Generate embedding
            query_embedding = await text_embedder.embed_text(f"{skill_name} thinking skill resources")
            
            # Build filter
            filter_condition = {
                "skill_name": {"$eq": skill_name.lower()},
                "content_type": {"$eq": "pdf"}
            }
            
            # Search in Pinecone
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
                filter=filter_condition
            )
            
            # Process results
            resources = []
            for match in results.matches:
                metadata = match.metadata
                
                resources.append({
                    "id": match.id,
                    "score": match.score,
                    "scaffold_type": metadata.get("scaffold_type", ""),
                    "file_name": metadata.get("file_name", ""),
                    "content_preview": metadata.get("content_preview", ""),
                    "pdf_url": self._create_resource_url(metadata.get("file_path")),
                    "image_url": self._create_resource_url(metadata.get("related_image")),
                    "video_url": self._create_resource_url(metadata.get("related_video"))
                })
            
            logger.info(f"Retrieved {len(resources)} resources for skill: {skill_name}")
            return resources
            
        except Exception as e:
            logger.error(f"Error retrieving resources for skill {skill_name}", error=str(e))
            return []
    
    def health_check(self) -> bool:
        """Check if the retriever is healthy"""
        try:
            if not self._index:
                return False
                
            # Simple query to test
            stats = self._index.describe_index_stats()
            return stats is not None
            
        except Exception as e:
            logger.error("Scaffold retriever health check failed", error=str(e))
            return False


# Global instance
scaffold_retriever = ScaffoldResourceRetriever()