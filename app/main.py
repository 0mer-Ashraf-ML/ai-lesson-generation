from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.config import settings
from app.utils.logging import configure_logging, get_logger
from app.utils.exceptions import (
    StructuralLearningException,
    ValidationError,
    SkillSelectionError,
    LLMGenerationError,
    RAGRetrievalError,
    DatabaseError,
    EmbeddingError
)

# Import routers
from app.api.routes import lesson, health

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Structural Learning AI API", version="1.0.0", environment=settings.environment)
    
    # Health check critical services on startup
    try:
        from app.database.supabase_client import supabase_client
        from app.core.generation.llm_client import llm_service
        
        # Test database connection
        db_healthy = await supabase_client.health_check()
        logger.info("Database health check", healthy=db_healthy)
        
        # Test LLM service
        llm_health = llm_service.health_check()
        logger.info("LLM service health check", status=llm_health)
        
    except Exception as e:
        logger.error("Startup health check failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Structural Learning AI API")


# Create FastAPI application
app = FastAPI(
    title="Structural Learning AI API",
    description="AI-powered lesson planning system using the Structural Learning Framework",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    logger.warning("Validation error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content={"error": "Validation Error", "message": str(exc)}
    )


@app.exception_handler(SkillSelectionError)
async def skill_selection_exception_handler(request, exc):
    logger.error("Skill selection error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content={"error": "Skill Selection Error", "message": str(exc)}
    )


@app.exception_handler(LLMGenerationError)
async def llm_generation_exception_handler(request, exc):
    logger.error("LLM generation error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={"error": "Content Generation Error", "message": "Failed to generate lesson content. Please try again."}
    )


@app.exception_handler(RAGRetrievalError)
async def rag_retrieval_exception_handler(request, exc):
    logger.error("RAG retrieval error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={"error": "Context Retrieval Error", "message": "Failed to retrieve curriculum context."}
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request, exc):
    logger.error("Database error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Database Error", "message": "A database error occurred."}
    )


@app.exception_handler(EmbeddingError)
async def embedding_exception_handler(request, exc):
    logger.error("Embedding error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={"error": "Embedding Error", "message": "Failed to process text embeddings."}
    )


@app.exception_handler(StructuralLearningException)
async def structural_learning_exception_handler(request, exc):
    logger.error("Structural Learning error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Application Error", "message": "An error occurred in the lesson planning system."}
    )


# Include routers
app.include_router(health.router)
app.include_router(lesson.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Structural Learning AI API",
        "version": "1.0.0",
        "description": "AI-powered lesson planning using the Structural Learning Framework",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.debug else "Contact administrator for documentation"
    }


# Run the application (for development)
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )