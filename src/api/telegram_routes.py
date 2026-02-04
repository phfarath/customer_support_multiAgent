"""
FastAPI routes for Telegram webhook integration
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import Dict, Any
import hmac
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from src.adapters.telegram_adapter import TelegramAdapter
from src.models import IngestMessageRequest, IngestChannel
from src.api.ingest_routes import ingest_message
from src.middleware.auth import verify_api_key
from src.middleware.rate_limiter import get_rate_limit_key_ip_only
from src.utils.sanitization import sanitize_text, sanitize_identifier, sanitize_company_id
from src.utils.secure_logging import SensitiveDataFilter
from src.config import settings
from slowapi import Limiter


# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Initialize rate limiter with IP-only key for public endpoints
limiter = Limiter(key_func=get_rate_limit_key_ip_only)
_WEBHOOK_DUMP_PATH = Path("logs/telegram_webhook.jsonl")

# Initialize PII filter for webhook logging
_pii_filter = SensitiveDataFilter()


def _redact_pii_from_webhook(update: dict) -> dict:
    """
    Redact PII from Telegram webhook payload before logging.

    Args:
        update: Raw Telegram update dict

    Returns:
        Sanitized copy with PII redacted
    """
    import copy

    sanitized = copy.deepcopy(update)

    def redact_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Redact known PII fields
                if key in ('first_name', 'last_name', 'username', 'phone_number'):
                    obj[key] = '[REDACTED]'
                elif key == 'text' and isinstance(value, str):
                    # Apply PII filter to message text
                    obj[key] = _pii_filter._mask_sensitive(value)
                elif isinstance(value, (dict, list)):
                    redact_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                redact_recursive(item)

    redact_recursive(sanitized)
    return sanitized


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

        # Log and persist with PII redaction
        redacted_update = _redact_pii_from_webhook(update)
        logger.info(f"Received Telegram webhook: {redacted_update}")
        try:
            _WEBHOOK_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _WEBHOOK_DUMP_PATH.open("a", encoding="utf-8") as f:
                # Write redacted version to prevent PII in logs
                f.write(json.dumps(redacted_update, ensure_ascii=True) + "\n")
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


def _validate_webhook_url(url: str) -> str:
    """
    Validate webhook URL to prevent SSRF attacks.

    Args:
        url: URL to validate

    Returns:
        Validated URL

    Raises:
        ValueError: If URL is invalid or potentially dangerous
    """
    try:
        parsed = urlparse(url)

        # Must be HTTPS in production
        if parsed.scheme not in ('https', 'http'):
            raise ValueError("URL must use HTTPS or HTTP protocol")

        # Block private/internal IP ranges
        hostname = parsed.hostname or ''

        # Block localhost variants
        if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
            raise ValueError("Localhost URLs are not allowed")

        # Block private IP ranges using regex
        private_ip_patterns = [
            r'^10\.',                          # 10.0.0.0/8
            r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0/12
            r'^192\.168\.',                    # 192.168.0.0/16
            r'^169\.254\.',                    # Link-local
        ]

        for pattern in private_ip_patterns:
            if re.match(pattern, hostname):
                raise ValueError("Private IP addresses are not allowed")

        # Ensure URL has a valid host
        if not parsed.netloc:
            raise ValueError("URL must have a valid host")

        return url

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid URL format: {str(e)}")


@router.post("/webhook/set")
@limiter.limit("5/minute")  # Critical admin operation
async def set_webhook(
    request: Request,  # Required by slowapi
    webhook_url: str = Query(..., description="HTTPS URL to receive webhook updates"),
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Set the Telegram webhook URL

    Requires: X-API-Key header

    Args:
        webhook_url: URL to receive webhook updates (must be HTTPS)
        api_key: Authenticated API key (auto-injected)

    Returns:
        Response from Telegram API
    """
    # Validate URL to prevent SSRF
    try:
        validated_url = _validate_webhook_url(webhook_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook URL: {str(e)}"
        )

    try:
        adapter = TelegramAdapter()
        result = await adapter.set_webhook(validated_url)
        return result
    except Exception as e:
        logger.error(f"Failed to set webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set webhook. Please check the URL and try again."
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
