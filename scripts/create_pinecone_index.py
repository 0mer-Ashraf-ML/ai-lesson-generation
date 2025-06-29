# scripts/create_pinecone_index.py
import asyncio
from pinecone import Pinecone, ServerlessSpec
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from app.config import settings
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

async def create_index():
    """Create a new Pinecone index"""
    try:
        # Use a simpler index name
        index_name = "scaffold-resources"
        
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Check if index already exists
        existing_indexes = pc.list_indexes().names()
        if index_name in existing_indexes:
            logger.info(f"Index '{index_name}' already exists")
            return index_name
        
        # Create new index
        logger.info(f"Creating index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI embedding dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.pinecone_environment
            )
        )
        
        logger.info(f"Index '{index_name}' created successfully!")
        
        # Update settings for future use
        logger.info("To use this index, update your .env file with:")
        logger.info(f"PINECONE_INDEX_NAME={index_name}")
        
        return index_name
    
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        return None

if __name__ == "__main__":
    index_name = asyncio.run(create_index())