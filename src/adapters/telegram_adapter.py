"""
Telegram adapter for handling Telegram Bot API webhooks and sending messages
"""
from typing import Dict, Any, Optional
from src.config import settings
from src.utils.http_client import get_http_client


class TelegramAdapter:
    """
    Adapter for Telegram Bot API integration
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize the Telegram adapter
        
        Args:
            bot_token: Telegram bot token (defaults to settings.telegram_bot_token)
        """
        self.bot_token = bot_token or getattr(settings, 'telegram_bot_token', None)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def parse_webhook_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a Telegram webhook update and extract relevant information
        
        Args:
            update: Telegram webhook update payload
            
        Returns:
            Dict with external_user_id, text, and metadata, or None if no message
        """
        # Extract message from update
        message = update.get("message", {})
        
        if not message:
            # Check for callback_query (button presses)
            callback_query = update.get("callback_query", {})
            if callback_query:
                message = callback_query.get("message", {})
                callback_data = callback_query.get("data", "")
                # Use callback data as text
                if message:
                    return {
                        "external_user_id": f"telegram:{message.get('from', {}).get('id')}",
                        "text": callback_data,
                        "metadata": {
                            "update_id": update.get("update_id"),
                            "callback_query_id": callback_query.get("id"),
                            "message_id": message.get("message_id"),
                            "chat_id": message.get("chat", {}).get("id"),
                            "chat_type": message.get("chat", {}).get("type"),
                            "username": message.get("from", {}).get("username"),
                            "first_name": message.get("from", {}).get("first_name"),
                            "last_name": message.get("from", {}).get("last_name"),
                        }
                    }
            return None
        
        # Extract user and chat information
        from_user = message.get("from", {})
        chat = message.get("chat", {})
        
        # Get text from message
        text = message.get("text") or message.get("caption", "")
        
        if not text:
            return None
        
        return {
            "external_user_id": f"telegram:{from_user.get('id')}",
            "text": text,
            "metadata": {
                "update_id": update.get("update_id"),
                "message_id": message.get("message_id"),
                "chat_id": chat.get("id"),
                "chat_type": chat.get("type"),
                "username": from_user.get("username"),
                "first_name": from_user.get("first_name"),
                "last_name": from_user.get("last_name"),
                "language_code": from_user.get("language_code"),
            }
        }
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message via Telegram Bot API
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, or None)
            disable_web_page_preview: Disable link previews
            
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        client = get_http_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """
        Answer a callback query (button press)
        
        Args:
            callback_query_id: Callback query ID
            text: Optional text to show
            show_alert: Whether to show as an alert
            
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/answerCallbackQuery"
        
        payload = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert
        }
        
        if text:
            payload["text"] = text
        
        client = get_http_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """
        Set the webhook for the bot
        
        Args:
            webhook_url: URL to receive webhook updates
            
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/setWebhook"
        
        payload = {"url": webhook_url}
        
        client = get_http_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """
        Get current webhook information
        
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/getWebhookInfo"
        
        client = get_http_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def delete_webhook(self) -> Dict[str, Any]:
        """
        Delete the webhook for the bot
        
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/deleteWebhook"
        
        client = get_http_client()
        response = await client.post(url)
        response.raise_for_status()
        return response.json()
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Get bot information
        
        Returns:
            Response from Telegram API
        """
        url = f"{self.api_url}/getMe"
        
        client = get_http_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
