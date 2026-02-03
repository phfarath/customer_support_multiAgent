"""
FastAPI routes for Telegram webhook integration
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends
from typing import Dict, Any
import hmac
import json
import logging
from pathlib import Path

from src.adapters.telegram_adapter import TelegramAdapter
from src.models import IngestMessageRequest, IngestChannel
from src.api.ingest_routes import ingest_message
from src.middleware.auth import verify_api_key
from src.middleware.rate_limiter import get_rate_limit_key_ip_only
from src.utils.sanitization import sanitize_text, sanitize_identifier, sanitize_company_id
from src.config import settings
from slowapi import Limiter


# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Initialize rate limiter with IP-only key for public endpoints
limiter = Limiter(key_func=get_rate_limit_key_ip_only)
_WEBHOOK_DUMP_PATH = Path("logs/telegram_webhook.jsonl")


async def verify_telegram_signature(request: Request) -> bool:
    """
    Verify Telegram webhook using secret token header.

    Telegram sends the secret token in the 'X-Telegram-Bot-Api-Secret-Token' header
    when the webhook is configured with a secret_token parameter.

    In development: Skip verification if secret not configured
    In production: Always require valid signature

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid or verification is skipped
    """
    # In development, skip verification if secret not configured
    if settings.environment != "production" and not settings.telegram_webhook_secret:
        logger.debug("Telegram webhook signature verification skipped (not configured in dev)")
        return True

    # Get the secret token from header
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if not secret_token:
        logger.warning(
            f"Telegram webhook request without signature from {request.client.host if request.client else 'unknown'}"
        )
        return False

    # Compare using constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(secret_token, settings.telegram_webhook_secret or ""):
        logger.warning(
            f"Invalid Telegram webhook signature from {request.client.host if request.client else 'unknown'}"
        )
        return False

    return True


@router.post("/webhook")
@limiter.limit("50/minute")  # Public endpoint (called by Telegram servers)
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """
    Telegram webhook endpoint

    This endpoint is PUBLIC (no API key required) as it's called by Telegram servers.
    Security is provided by webhook signature verification using the secret token
    configured when setting up the webhook with Telegram.

    This endpoint receives updates from Telegram Bot API:
    1. Verifies the webhook signature (in production)
    2. Parses the Telegram update payload
    3. Converts it to the standard ingest format
    4. Calls the /ingest-message endpoint
    5. Sends the response back to the user via Telegram

    Args:
        request: FastAPI request with Telegram webhook payload

    Returns:
        Success response

    Raises:
        HTTPException 403: If webhook signature verification fails
    """
    # Verify Telegram webhook signature
    if not await verify_telegram_signature(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )

    try:
        # Get Telegram update from request body
        update = await request.json()
        logger.info(f"Received Telegram webhook: {update}")
        try:
            _WEBHOOK_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _WEBHOOK_DUMP_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(update, ensure_ascii=True) + "\n")
        except Exception as dump_error:
            logger.warning(f"Failed to persist webhook payload: {dump_error}")
        
        # Initialize Telegram adapter
        adapter = TelegramAdapter()
        
        # Parse the webhook update
        parsed = adapter.parse_webhook_update(update)
        logger.info(f"Parsed webhook update: {parsed}")
        
        if not parsed:
            logger.warning(f"Received update without message: {update.get('update_id')}")
            return {"status": "ok", "message": "No message to process"}

        # SANITIZE INPUTS from Telegram
        try:
            text = sanitize_text(parsed["text"], max_length=4000)
            external_user_id = sanitize_identifier(parsed["external_user_id"])

            # Sanitize company_id if present
            company_id = parsed["metadata"].get("company_id")
            if company_id:
                company_id = sanitize_company_id(company_id)
        except ValueError as e:
            logger.warning(f"Input validation failed for Telegram message: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input: {str(e)}"
            )

        # Extract chat_id for sending reply
        chat_id = parsed["metadata"].get("chat_id")
        callback_query_id = parsed["metadata"].get("callback_query_id")

        # Create ingest message request (using sanitized values)
        ingest_request = IngestMessageRequest(
            channel=IngestChannel.TELEGRAM,
            external_user_id=external_user_id,
            text=text,
            metadata=parsed["metadata"],
            company_id=company_id
        )

        # Process the message through the ingest endpoint
        logger.info(f"Calling ingest_message with: {ingest_request}")
        response = await ingest_message(ingest_request)
        logger.info(f"Received response from ingest_message: {response}")
        
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
@limiter.limit("30/minute")  # Admin endpoint
async def get_webhook_info(
    request: Request,  # Required by slowapi
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get current Telegram webhook information

    Requires: X-API-Key header

    Args:
        api_key: Authenticated API key (auto-injected)

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
@limiter.limit("5/minute")  # Critical admin operation
async def set_webhook(
    request: Request,  # Required by slowapi
    webhook_url: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Set the Telegram webhook URL

    Requires: X-API-Key header

    Args:
        webhook_url: URL to receive webhook updates
        api_key: Authenticated API key (auto-injected)

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
@limiter.limit("5/minute")  # Critical admin operation
async def delete_webhook(
    request: Request,  # Required by slowapi
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Delete the Telegram webhook

    Requires: X-API-Key header

    Args:
        api_key: Authenticated API key (auto-injected)

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
@limiter.limit("30/minute")  # Admin endpoint
async def get_bot_info(
    request: Request,  # Required by slowapi
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get bot information from Telegram

    Requires: X-API-Key header

    Args:
        api_key: Authenticated API key (auto-injected)

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
