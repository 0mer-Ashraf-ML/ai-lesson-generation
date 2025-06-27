from supabase import create_client, Client
from app.config import settings
from app.utils.logging import get_logger
from typing import Optional

logger = get_logger(__name__)


class SupabaseClient:
    """Supabase client wrapper"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Get the regular Supabase client"""
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Supabase client initialized")
        return self._client
    
    @property
    def service_client(self) -> Client:
        """Get the service role Supabase client (for admin operations)"""
        if self._service_client is None:
            self._service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
            logger.info("Supabase service client initialized")
        return self._service_client
    
    async def health_check(self) -> bool:
        """Check if Supabase is healthy"""
        try:
            # Simple query to test connection
            result = self.client.table('profiles').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.error("Supabase health check failed", error=str(e))
            return False


# Global instance
supabase_client = SupabaseClient()