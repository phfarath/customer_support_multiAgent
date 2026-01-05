"""
FastAPI routes for Telegram webhook integration
"""
from fastapi import APIRouter, HTTPException, status, Request
from typing import Dict, Any
import logging

from src.adapters.telegram_adapter import TelegramAdapter
from src.models import IngestMessageRequest, IngestChannel
from src.api.ingest_routes import ingest_message


# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """
    Telegram webhook endpoint
    
    This endpoint receives updates from Telegram Bot API:
    1. Parses the Telegram update payload
    2. Converts it to the standard ingest format
    3. Calls the /ingest-message endpoint
    4. Sends the response back to the user via Telegram
    
    Args:
        request: FastAPI request with Telegram webhook payload
        
    Returns:
        Success response
    """
    try:
        # Get Telegram update from request body
        update = await request.json()
        
        # Initialize Telegram adapter
        adapter = TelegramAdapter()
        
        # Parse the webhook update
        parsed = adapter.parse_webhook_update(update)
        
        if not parsed:
            logger.warning(f"Received update without message: {update.get('update_id')}")
            return {"status": "ok", "message": "No message to process"}
        
        # Extract chat_id for sending reply
        chat_id = parsed["metadata"].get("chat_id")
        callback_query_id = parsed["metadata"].get("callback_query_id")
        
        # Create ingest message request
        ingest_request = IngestMessageRequest(
            channel=IngestChannel.TELEGRAM,
            external_user_id=parsed["external_user_id"],
            text=parsed["text"],
            metadata=parsed["metadata"]
        )
        
        # Process the message through the ingest endpoint
        response = await ingest_message(ingest_request)
        
        # Send the reply back to Telegram
        if chat_id and response.reply_text:
            await adapter.send_message(
                chat_id=chat_id,
                text=response.reply_text
            )
        
        # Answer callback query if this was a button press
        if callback_query_id:
            await adapter.answer_callback_query(
                callback_query_id=callback_query_id
            )
        
        logger.info(
            f"Processed Telegram message from {parsed['external_user_id']}, "
            f"ticket_id: {response.ticket_id}, escalated: {response.escalated}"
        )
        
        return {
            "status": "ok",
            "message": "Message processed successfully",
            "ticket_id": response.ticket_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/webhook/info")
async def get_webhook_info() -> Dict[str, Any]:
    """
    Get current Telegram webhook information
    
    Returns:
        Webhook information from Telegram API
    """
    try:
        adapter = TelegramAdapter()
        info = await adapter.get_webhook_info()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook info: {str(e)}"
        )


@router.post("/webhook/set")
async def set_webhook(webhook_url: str) -> Dict[str, Any]:
    """
    Set the Telegram webhook URL
    
    Args:
        webhook_url: URL to receive webhook updates
        
    Returns:
        Response from Telegram API
    """
    try:
        adapter = TelegramAdapter()
        result = await adapter.set_webhook(webhook_url)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set webhook: {str(e)}"
        )


@router.post("/webhook/delete")
async def delete_webhook() -> Dict[str, Any]:
    """
    Delete the Telegram webhook
    
    Returns:
        Response from Telegram API
    """
    try:
        adapter = TelegramAdapter()
        result = await adapter.delete_webhook()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )


@router.get("/bot/info")
async def get_bot_info() -> Dict[str, Any]:
    """
    Get bot information from Telegram
    
    Returns:
        Bot information from Telegram API
    """
    try:
        adapter = TelegramAdapter()
        info = await adapter.get_me()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot info: {str(e)}"
        )
