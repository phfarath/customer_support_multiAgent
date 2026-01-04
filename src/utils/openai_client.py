"""
OpenAI Client - Helper for making OpenAI API calls
"""
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from src.config import settings


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
        temperature: float = 0.7,
        max_tokens: int = 500,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Make a chat completion request to OpenAI
        
        Args:
            system_prompt: System message defining the AI's role
            user_message: User message to process
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            response_format: Optional JSON mode specification
            
        Returns:
            Generated response text
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")
    
    async def json_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Make a chat completion request that returns JSON
        
        Args:
            system_prompt: System message defining the AI's role
            user_message: User message to process
            temperature: Sampling temperature (lower for more deterministic JSON)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Parsed JSON response
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
