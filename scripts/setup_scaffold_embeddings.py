"""
Script to create embeddings for scaffold PDFs (BuildIt, SayIt, MapIt) and store them in Pinecone
"""

import asyncio
import sys
from pathlib import Path
import fitz  # PyMuPDF

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from pinecone import Pinecone
import openai
from app.config import settings
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


class ScaffoldEmbeddingGenerator:
    """Generate embeddings for scaffold PDFs"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions
        self.base_dir = Path(__file__).parent.parent / "data"  # Assuming data/ is at project root
    
    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from a PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {pdf_path}", error=str(e))
            return ""
    
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {text[:50]}...", error=str(e))
            raise
    
    async def process_scaffold_pdfs(self) -> list:
        """Process all scaffold PDFs and generate embeddings with metadata"""
        vectors = []
        scaffold_types = ["buildit-data", "sayit-data", "mapit-data"]
        
        for scaffold_type in scaffold_types:
            # Normalize scaffold type for metadata
            normalized_scaffold = scaffold_type.replace("-data", "")
            
            scaffold_dir = self.base_dir / scaffold_type
            pdf_dir = scaffold_dir / "pdf-data"
            
            # Skip if directory doesn't exist
            if not pdf_dir.exists():
                logger.warning(f"PDF directory not found: {pdf_dir}")
                continue
            
            logger.info(f"Processing PDFs in {pdf_dir}")
            
            # Get all PDF files
            pdf_files = list(pdf_dir.glob("**/*.pdf"))
            if not pdf_files:
                logger.warning(f"No PDF files found in {pdf_dir}")
                continue
            
            logger.info(f"Found {len(pdf_files)} PDF files in {scaffold_type}")
            
            # Process each PDF
            for pdf_path in pdf_files:
                try:
                    # Extract file name and parent directory (skill name)
                    file_name = pdf_path.name
                    parent_dir = pdf_path.parent.name
                    
                    # If PDF is directly in pdf-data, use filename as skill
                    skill_name = parent_dir if parent_dir != "pdf-data" else file_name.replace(".pdf", "")
                    
                    # Extract text from PDF
                    text = await self.extract_text_from_pdf(str(pdf_path))
                    if not text:
                        logger.warning(f"No text extracted from {pdf_path}")
                        continue
                    
                    # Create vector ID
                    vector_id = f"{normalized_scaffold}-{skill_name}-{file_name.replace('.pdf', '').replace(' ', '_')}"
                    
                    # Generate embedding
                    embedding = await self.generate_embedding(text)
                    
                    # Create vector with metadata
                    vector = {
                        "id": vector_id,
                        "values": embedding,
                        "metadata": {
                            "scaffold_type": normalized_scaffold,
                            "skill_name": skill_name,
                            "file_name": file_name,
                            "content_type": "pdf",
                            "file_path": str(pdf_path.relative_to(self.base_dir)),
                            "content_preview": text[:300] + "..." if len(text) > 300 else text,
                            # Check for image in related folders (using conventional naming)
                            # "related_image": str(scaffold_dir / "images" / f"{skill_name}.png") 
                            #     if (scaffold_dir / "images" / f"{skill_name}.png").exists() else None,
                            # "related_video": str(scaffold_dir / "videos" / f"{skill_name}.mp4")
                            #     if (scaffold_dir / "videos" / f"{skill_name}.mp4").exists() else None
                        }
                    }
                    
                    vectors.append(vector)
                    logger.info(f"Processed PDF: {file_name}", scaffold=normalized_scaffold, skill=skill_name)
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing PDF {pdf_path}", error=str(e))
        
        return vectors


async def upsert_to_pinecone(vectors: list):
    """Upsert vectors to Pinecone index"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        
        # Upsert vectors in batches
        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1}")
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        # Verify the upsert
        stats = index.describe_index_stats()
        logger.info("Vectors upserted successfully", 
                   total_vectors=stats.total_vector_count,
                   vectors_added=len(vectors))
                   
        return True
        
    except Exception as e:
        logger.error("Failed to upsert vectors to Pinecone", error=str(e))
        return False


async def verify_pinecone_index():
    """Verify that the Pinecone index exists or create it"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Check if index exists
        indexes = pc.list_indexes().names()
        
        if settings.pinecone_index_name not in indexes:
            logger.info(f"Pinecone index '{settings.pinecone_index_name}' does not exist, creating it...")
            
            # Import the create_pinecone_index function from setup_pinecone.py
            from setup_pinecone import create_pinecone_index
            
            # Create the index
            index_created = await create_pinecone_index()
            if not index_created:
                logger.error("Failed to create Pinecone index")
                return False
                
            # Wait for index to be ready
            logger.info("Waiting for index to be fully ready...")
            await asyncio.sleep(60)
        
        return True
        
    except Exception as e:
        logger.error("Failed to verify Pinecone index", error=str(e))
        return False


async def test_scaffold_query(scaffold_type: str, skill_name: str):
    """Test querying the Pinecone index for scaffold resources"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        
        # Generate embedding for test query
        embedding_gen = ScaffoldEmbeddingGenerator()
        query_text = f"{scaffold_type} {skill_name} teaching resource"
        query_embedding = await embedding_gen.generate_embedding(query_text)
        
        # Search in Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_values=False,
            include_metadata=True,
            filter={
                "scaffold_type": {"$eq": scaffold_type}
            }
        )
        
        logger.info("Query test successful", results_count=len(results.matches))
        
        for i, match in enumerate(results.matches):
            logger.info(
                f"Result {i+1}",
                id=match.id,
                score=round(match.score, 3),
                scaffold=match.metadata.get('scaffold_type'),
                skill=match.metadata.get('skill_name'),
                file_name=match.metadata.get('file_name'),
                related_image=match.metadata.get('related_image'),
                content_preview=match.metadata.get('content_preview', '')[:100] + "..."
            )
        
        return True
        
    except Exception as e:
        logger.error("Scaffold query test failed", error=str(e))
        return False


async def main():
    """Main function to process scaffold PDFs and create embeddings"""
    logger.info("Starting scaffold PDF embedding process")
    
    # Verify OpenAI API key
    try:
        openai.OpenAI(api_key=settings.openai_api_key).models.list()
        logger.info("OpenAI API key verified")
    except Exception as e:
        logger.error("OpenAI API key verification failed", error=str(e))
        return False
    
    # Verify Pinecone index
    index_verified = await verify_pinecone_index()
    if not index_verified:
        logger.error("Failed to verify Pinecone index")
        return False
    
    # Process scaffold PDFs
    logger.info("Processing scaffold PDFs...")
    embedding_generator = ScaffoldEmbeddingGenerator()
    vectors = await embedding_generator.process_scaffold_pdfs()
    
    if not vectors:
        logger.error("No vectors generated from PDFs")
        return False
    
    logger.info(f"Generated {len(vectors)} vectors from scaffold PDFs")
    
    # Upsert vectors to Pinecone
    upsert_success = await upsert_to_pinecone(vectors)
    if not upsert_success:
        logger.error("Failed to upsert vectors to Pinecone")
        return False
    
    # Wait for indexing to complete
    logger.info("Waiting for indexing to complete...")
    await asyncio.sleep(15)
    
    # Test queries
    logger.info("Testing scaffold queries...")
    
    # Test a query for each scaffold type
    test_queries = [
        ("buildit", "hypothesise"),
        ("sayit", "explain"),
        ("mapit", "categorise")
    ]
    
    for scaffold_type, skill_name in test_queries:
        logger.info(f"Testing query for {scaffold_type} - {skill_name}")
        query_success = await test_scaffold_query(scaffold_type, skill_name)
        if not query_success:
            logger.warning(f"Query test for {scaffold_type} - {skill_name} failed")
    
    logger.info("Scaffold PDF embedding process completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)