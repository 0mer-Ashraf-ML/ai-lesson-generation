from fastapi import APIRouter, status
from app.models.responses import HealthResponse
from app.database.supabase_client import supabase_client
from app.core.generation.llm_client import llm_service
from app.core.rag.retriever import curriculum_retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint
    
    Returns:
        Health status and timestamp
    """
    return HealthResponse(status="healthy")


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check including all services
    
    Returns:
        Detailed health status of all components
    """
    health_status = {
        "api": "healthy",
        "timestamp": None  # Will be set by HealthResponse
    }
    
    # Check Supabase connection
    try:
        supabase_healthy = await supabase_client.health_check()
        health_status["supabase"] = "healthy" if supabase_healthy else "unhealthy"
    except Exception as e:
        logger.error("Supabase health check failed", error=str(e))
        health_status["supabase"] = "unhealthy"
    
    # Check LLM service
    try:
        llm_health = llm_service.health_check()
        health_status["llm_service"] = llm_health
    except Exception as e:
        logger.error("LLM health check failed", error=str(e))
        health_status["llm_service"] = {"primary_client": False, "fallback_client": None}
    
    # Check Pinecone/RAG
    try:
        pinecone_healthy = curriculum_retriever.health_check()
        health_status["pinecone"] = "healthy" if pinecone_healthy else "unhealthy"
    except Exception as e:
        logger.error("Pinecone health check failed", error=str(e))
        health_status["pinecone"] = "unhealthy"
    
    # Determine overall health
    critical_services = ["supabase", "llm_service"]
    overall_healthy = True
    
    for service in critical_services:
        if service == "llm_service":
            if not health_status[service].get("primary_client", False):
                overall_healthy = False
                break
        elif health_status[service] != "healthy":
            overall_healthy = False
            break
    
    health_status["overall"] = "healthy" if overall_healthy else "degraded"
    
    # Log health status
    logger.info("Health check completed", status=health_status)
    
    return health_status