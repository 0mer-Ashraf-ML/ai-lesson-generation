import openai
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from app.config import settings
from app.utils.exceptions import LLMGenerationError
from app.utils.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content from prompt"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the LLM service is available"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI GPT client for content generation"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.default_model = "gpt-4o-mini"  # Cost-effective for MVP
        self.advanced_model = "gpt-4.1"  # For complex generation if needed
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def generate(
        self, 
        prompt: str, 
        use_advanced_model: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate content using OpenAI GPT
        
        Args:
            prompt: The prompt to send to the model
            use_advanced_model: Whether to use GPT-4 instead of GPT-3.5
            temperature: Creativity level (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dictionary containing the generated content and metadata
        """
        try:
            model = self.advanced_model if use_advanced_model else self.default_model
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educator who creates high-quality, age-appropriate lesson activities. Always return valid JSON as requested."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Ensure JSON output
            )
            
            # Extract the generated content
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                logger.error("LLM returned invalid JSON", content=content[:200])
                raise LLMGenerationError("LLM returned invalid JSON format")
            
            # Create response with metadata
            result = {
                'content': parsed_content,
                'model': model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'finish_reason': response.choices[0].finish_reason
            }
            
            logger.info(
                "LLM generation successful",
                model=model,
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason
            )
            
            return result
            
        except openai.RateLimitError as e:
            logger.error("OpenAI rate limit exceeded", error=str(e))
            raise LLMGenerationError("Rate limit exceeded - please try again later")
            
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e))
            raise LLMGenerationError(f"API error: {str(e)}")
            
        except Exception as e:
            logger.error("Unexpected error in LLM generation", error=str(e))
            raise LLMGenerationError(f"Generation failed: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Simple API call to test connectivity
            self.client.models.list()
            return True
        except Exception as e:
            logger.error("OpenAI health check failed", error=str(e))
            return False


class LLMService:
    """Service that manages LLM clients and provides generation interface"""
    
    def __init__(self):
        self.primary_client = OpenAIClient()
        # Future: Add Claude client as backup
        self.fallback_client = None
    
    async def generate_lesson_block(
        self,
        prompt: str,
        complexity: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a lesson block using the appropriate LLM
        
        Args:
            prompt: The generation prompt
            complexity: 'simple' or 'standard' or 'advanced'
            
        Returns:
            Generated content with metadata
        """
        try:
            # Determine model selection based on complexity
            use_advanced = complexity == "advanced"
            
            # Adjust parameters based on complexity
            temperature = 0.6 if complexity == "simple" else 0.7
            max_tokens = 800 if complexity == "simple" else 1200
            
            result = await self.primary_client.generate(
                prompt=prompt,
                use_advanced_model=use_advanced,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return result
            
        except LLMGenerationError as e:
            # Try fallback if available
            if self.fallback_client:
                logger.warning("Primary LLM failed, trying fallback", error=str(e))
                try:
                    return await self.fallback_client.generate(prompt, **kwargs)
                except Exception as fallback_error:
                    logger.error("Fallback LLM also failed", error=str(fallback_error))
            
            # Re-raise original error if no fallback or fallback failed
            raise e
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all LLM clients"""
        health_status = {
            'primary_client': self.primary_client.health_check(),
            'fallback_client': self.fallback_client.health_check() if self.fallback_client else None
        }
        
        return health_status


# Global instance
llm_service = LLMService()