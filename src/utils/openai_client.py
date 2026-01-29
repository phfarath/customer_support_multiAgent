"""
OpenAI Client - Helper for making OpenAI API calls

Includes security guardrails:
- Maximum temperature limit to prevent unpredictable outputs
- Maximum token limits to prevent resource exhaustion
- Safe JSON parsing with fallback
"""
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

# Security constants - enforce safe limits
MAX_TEMPERATURE = 0.7  # Maximum allowed temperature
SAFE_TEMPERATURE = 0.4  # Recommended safe temperature for production
MAX_TOKENS_LIMIT = 2000  # Maximum allowed tokens
DEFAULT_MAX_TOKENS = 600  # Default token limit


class OpenAIClient:
    """
    Wrapper for OpenAI API calls with retry logic and error handling
    """
    
    def __init__(self):
        """Initialize the OpenAI client"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")
        
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = SAFE_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Make a chat completion request to OpenAI

        Args:
            system_prompt: System message defining the AI's role
            user_message: User message to process
            temperature: Sampling temperature (0-2), capped at MAX_TEMPERATURE
            max_tokens: Maximum tokens to generate, capped at MAX_TOKENS_LIMIT
            response_format: Optional JSON mode specification

        Returns:
            Generated response text

        Note:
            Temperature and max_tokens are capped to safe limits for security.
        """
        # SECURITY: Enforce safe limits
        safe_temperature = min(temperature, MAX_TEMPERATURE)
        safe_max_tokens = min(max_tokens, MAX_TOKENS_LIMIT)

        if temperature > MAX_TEMPERATURE:
            logger.warning(
                f"Temperature {temperature} exceeds MAX_TEMPERATURE {MAX_TEMPERATURE}, "
                f"capping to {safe_temperature}"
            )

        if max_tokens > MAX_TOKENS_LIMIT:
            logger.warning(
                f"max_tokens {max_tokens} exceeds MAX_TOKENS_LIMIT {MAX_TOKENS_LIMIT}, "
                f"capping to {safe_max_tokens}"
            )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": safe_temperature,
                "max_tokens": safe_max_tokens
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")
    
    async def json_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        fallback_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a chat completion request that returns JSON

        Args:
            system_prompt: System message defining the AI's role
            user_message: User message to process
            temperature: Sampling temperature (lower for more deterministic JSON)
            max_tokens: Maximum tokens to generate
            fallback_response: Optional fallback if JSON parsing fails

        Returns:
            Parsed JSON response

        Note:
            If JSON parsing fails and fallback_response is provided,
            returns the fallback instead of raising an exception.
        """
        import json

        response_text = await self.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {str(e)}")
            logger.debug(f"Raw response: {response_text[:500]}")

            # SECURITY: Return safe fallback instead of crashing
            if fallback_response is not None:
                logger.info("Using fallback response due to JSON parsing failure")
                return fallback_response

            raise RuntimeError(f"Failed to parse OpenAI JSON response: {str(e)}")


# Singleton instance
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """
    Get or create the singleton OpenAI client instance
    
    Returns:
        OpenAIClient instance
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client
