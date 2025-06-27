#!/usr/bin/env python3
"""
Script to set up Pinecone index for RAG curriculum retrieval with real OpenAI embeddings
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from pinecone import Pinecone, ServerlessSpec
import openai
from app.config import settings
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate real embeddings using OpenAI"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions, cost-effective
    
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


async def create_pinecone_index():
    """Create the Pinecone index for curriculum documents"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)

        index_name = settings.pinecone_index_name
        index_exists = index_name in pc.list_indexes().names()

        if index_exists:
            logger.info("Pinecone index already exists", index_name=index_name)
            return True

        logger.info("Creating Pinecone index", index_name=index_name)

        pc.create_index(
            name=index_name,
            dimension=1536,  # text-embedding-3-small dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.pinecone_environment
            )
        )

        # Wait for index to be ready
        logger.info("Waiting for index to be ready...")
        max_retries = 60  # Increased timeout
        for i in range(max_retries):
            try:
                index = pc.Index(index_name)
                stats = index.describe_index_stats()
                if stats is not None:
                    logger.info("Pinecone index created successfully", index_name=index_name)
                    return True
            except Exception as e:
                logger.debug("Index not ready yet", attempt=i + 1, error=str(e))
                time.sleep(5)  # Wait longer between checks

        logger.error("Index creation timed out")
        return False

    except Exception as e:
        logger.error("Failed to create Pinecone index", error=str(e))
        return False


async def upsert_sample_documents():
    """Upsert sample curriculum documents with real OpenAI embeddings"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        
        # Initialize embedding generator
        embedding_gen = EmbeddingGenerator()

        # Sample curriculum documents with full content
        sample_docs_content = [
            {
                "id": "uk-ks2-science-states-matter-1",
                "content": "States of matter include solids, liquids, and gases. Solids have a fixed shape and volume because their particles are tightly packed and vibrate in fixed positions. Liquids have a fixed volume but take the shape of their container because particles are close together but can move around each other. Gases have no fixed shape or volume because particles are far apart and move freely in all directions. Understanding states of matter helps us explain everyday phenomena like melting ice, boiling water, and steam formation.",
                "metadata": {
                    "subject": "Science",
                    "grade": "Year 4",
                    "curriculum": "UK KS2",
                    "chunk_type": "curriculum_content",
                    "source": "UK National Curriculum Key Stage 2 Science",
                    "topic": "States of Matter"
                }
            },
            {
                "id": "uk-ks2-science-materials-properties-1",
                "content": "Materials can be classified by their properties such as hardness, solubility, transparency, conductivity, and magnetic behavior. Hard materials like diamond and steel resist scratching, while soft materials like clay and rubber can be easily shaped. Soluble materials like salt dissolve in water, while insoluble materials like oil do not mix with water. Transparent materials like glass allow light to pass through, opaque materials block light completely, and translucent materials allow some light through. Understanding material properties helps us choose the right material for specific purposes in construction, clothing, and everyday objects.",
                "metadata": {
                    "subject": "Science",
                    "grade": "Year 4",
                    "curriculum": "UK KS2",
                    "chunk_type": "curriculum_content",
                    "source": "UK National Curriculum Key Stage 2 Science",
                    "topic": "Material Properties"
                }
            },
            {
                "id": "compare-strategy-example-1",
                "content": "When using the Compare thinking skill, students should identify both similarities and differences between objects, concepts, or ideas. Use graphic organizers like Venn diagrams to visually organize comparisons, with shared characteristics in the overlapping section and unique features in separate sections. Encourage students to look beyond surface features and consider deeper connections like function, purpose, or underlying principles. Effective comparison activities help students develop analytical thinking and see relationships between different concepts.",
                "metadata": {
                    "subject": "General",
                    "grade": "All",
                    "curriculum": "Structural Learning",
                    "chunk_type": "instructional_strategy",
                    "strategy_type": "Compare",
                    "skill": "Compare",
                    "block_type": "MapIt",
                    "example_activity": "Compare two animals using a Venn diagram to show similarities and differences in habitat, diet, and physical features"
                }
            },
            {
                "id": "categorise-strategy-example-1",
                "content": "The Categorise thinking skill helps students organize information into meaningful groups based on shared characteristics or criteria. Provide clear sorting criteria and allow students to explain their reasoning for grouping decisions. Use sorting activities, classification charts, or grouping exercises with physical objects or concepts. Encourage students to consider multiple ways to categorize the same items and discuss which grouping method is most useful for different purposes. This skill develops logical thinking and helps students see patterns and relationships in complex information.",
                "metadata": {
                    "subject": "General",
                    "grade": "All",
                    "curriculum": "Structural Learning",
                    "chunk_type": "instructional_strategy",
                    "strategy_type": "Categorise",
                    "skill": "Categorise",
                    "block_type": "MapIt",
                    "example_activity": "Sort classroom objects by material (wood, plastic, metal) and discuss the grouping criteria and alternative sorting methods"
                }
            },
            {
                "id": "uk-ks2-math-fractions-1",
                "content": "Fractions represent parts of a whole or parts of a group. The denominator shows how many equal parts the whole is divided into, while the numerator shows how many of those parts we have. Students should understand fractions as numbers that can be placed on a number line between whole numbers. Equivalent fractions represent the same amount but use different numbers, like 1/2 = 2/4 = 3/6. Students should be able to compare fractions with the same denominator by comparing numerators, and recognize that fractions with larger denominators represent smaller parts when numerators are the same.",
                "metadata": {
                    "subject": "Mathematics",
                    "grade": "Year 4",
                    "curriculum": "UK KS2",
                    "chunk_type": "curriculum_content",
                    "source": "UK National Curriculum Key Stage 2 Mathematics",
                    "topic": "Fractions"
                }
            },
            {
                "id": "explain-strategy-example-1",
                "content": "The Explain thinking skill helps students communicate their understanding clearly and logically. Encourage students to use evidence and reasoning to support their explanations, not just state facts. Provide sentence starters like 'This happens because...', 'The reason is...', and 'I can explain this by...' to scaffold their explanations. Model clear explanation techniques by thinking aloud and showing how to structure explanations with cause and effect, step-by-step processes, or logical reasoning. Good explanations demonstrate deep understanding and help students clarify their own thinking.",
                "metadata": {
                    "subject": "General",
                    "grade": "All",
                    "curriculum": "Structural Learning",
                    "chunk_type": "instructional_strategy",
                    "strategy_type": "Explain",
                    "skill": "Explain",
                    "block_type": "SayIt",
                    "example_activity": "Explain why ice melts when heated, using scientific vocabulary and cause-effect relationships"
                }
            },
            {
                "id": "hypothesise-strategy-example-1",
                "content": "The Hypothesise thinking skill engages students in making evidence-based predictions that can be tested. Encourage students to use their prior knowledge and observations to form reasonable hypotheses using 'If... then...' statements. Provide opportunities to test hypotheses through experiments, research, or exploration. Help students understand that hypotheses can be incorrect and that learning occurs through testing and refining ideas. This skill develops scientific thinking and encourages students to think critically about cause and effect relationships.",
                "metadata": {
                    "subject": "General",
                    "grade": "All",
                    "curriculum": "Structural Learning",
                    "chunk_type": "instructional_strategy",
                    "strategy_type": "Hypothesise",
                    "skill": "Hypothesise",
                    "block_type": "BuildIt",
                    "example_activity": "Predict which materials will float or sink in water, then test hypotheses and explain results"
                }
            }
        ]

        logger.info("Generating embeddings for sample documents...")
        
        # Generate embeddings for each document
        sample_docs_with_embeddings = []
        for doc in sample_docs_content:
            logger.info(f"Generating embedding for document: {doc['id']}")
            
            # Generate embedding for the content
            embedding = await embedding_gen.generate_embedding(doc['content'])
            
            # Create the document with embedding
            pinecone_doc = {
                "id": doc["id"],
                "values": embedding,
                "metadata": {
                    **doc["metadata"],
                    "content": doc["content"]  # Store content in metadata for retrieval
                }
            }
            
            sample_docs_with_embeddings.append(pinecone_doc)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        logger.info("Upserting documents to Pinecone...")
        
        # Upsert documents in smaller batches
        batch_size = 10
        for i in range(0, len(sample_docs_with_embeddings), batch_size):
            batch = sample_docs_with_embeddings[i:i + batch_size]
            index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1}/{(len(sample_docs_with_embeddings)-1)//batch_size + 1}")

        # Wait for indexing to complete
        await asyncio.sleep(10)
        
        # Verify the upsert
        stats = index.describe_index_stats()
        logger.info("Sample documents upserted successfully", 
                   total_vectors=stats.total_vector_count,
                   documents_added=len(sample_docs_with_embeddings))

        return True

    except Exception as e:
        logger.error("Failed to upsert sample documents", error=str(e))
        return False


async def test_pinecone_query():
    """Test querying the Pinecone index with real embeddings"""
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        
        embedding_gen = EmbeddingGenerator()
        
        # Test query about states of matter
        test_query = "What are the properties of solids, liquids, and gases?"
        logger.info(f"Testing query: {test_query}")
        
        # Generate embedding for test query
        query_embedding = await embedding_gen.generate_embedding(test_query)
        
        # Search in Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_values=False,
            include_metadata=True,
            filter={"curriculum": {"$eq": "UK KS2"}}
        )
        
        logger.info("Query test successful", results_count=len(results.matches))
        
        for i, match in enumerate(results.matches):
            logger.info(
                f"Result {i+1}",
                id=match.id,
                score=round(match.score, 3),
                subject=match.metadata.get('subject'),
                topic=match.metadata.get('topic'),
                content_preview=match.metadata.get('content', '')[:100] + "..."
            )
        
        return True

    except Exception as e:
        logger.error("Pinecone query test failed", error=str(e))
        return False


async def main():
    """Main setup function"""
    logger.info("Starting Pinecone setup with real OpenAI embeddings")
    
    # Verify OpenAI API key
    try:
        openai.OpenAI(api_key=settings.openai_api_key).models.list()
        logger.info("OpenAI API key verified")
    except Exception as e:
        logger.error("OpenAI API key verification failed", error=str(e))
        return False
    
    # Create index
    index_created = await create_pinecone_index()
    if not index_created:
        logger.error("Failed to create Pinecone index")
        return False

    # Wait for index to be fully ready
    logger.info("Waiting for index to be fully ready...")
    await asyncio.sleep(10)

    # Upsert sample documents with real embeddings
    docs_upserted = await upsert_sample_documents()
    if not docs_upserted:
        logger.error("Failed to upsert sample documents")
        return False

    # Wait for indexing to complete
    logger.info("Waiting for indexing to complete...")
    await asyncio.sleep(15)

    # Test querying
    query_test = await test_pinecone_query()
    if not query_test:
        logger.error("Pinecone query test failed")
        return False

    logger.info("Pinecone setup with real embeddings completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)