from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # API Configuration
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # OpenAI
    openai_api_key: str
    
    # Pinecone
    pinecone_api_key: str
    pinecone_environment: str
    pinecone_index_name: str = "structural-learning-curriculum"
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    
    # App Settings
    secret_key: str
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Future extension points
    enable_feedback_collection: bool = False
    enable_block_regeneration: bool = False
    prompt_version: str = "v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()