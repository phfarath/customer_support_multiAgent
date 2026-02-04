"""
FastAPI routes for WhatsApp Business API webhook integration

Based on WhatsApp Cloud API documentation:
https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks
"""
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query, Response
from typing import Dict, Any
import json
import logging
from pathlib import Path

from src.adapters.whatsapp_adapter import WhatsAppAdapter
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

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Initialize rate limiter with IP-only key for public endpoints
limiter = Limiter(key_func=get_rate_limit_key_ip_only)
_WEBHOOK_DUMP_PATH = Path("logs/whatsapp_webhook.jsonl")

# Initialize PII filter for webhook logging
_pii_filter = SensitiveDataFilter()


def _redact_pii_from_webhook(payload: dict) -> dict:
    """
    Redact PII from WhatsApp webhook payload before logging.

    Args:
        payload: Raw WhatsApp webhook dict

    Returns:
        Sanitized copy with PII redacted
    """
    import copy

    sanitized = copy.deepcopy(payload)

    def redact_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Redact known PII fields
                if key in ("wa_id", "from", "to", "phone_number", "display_phone_number"):
                    if isinstance(value, str) and len(value) > 4:
                        # Keep last 4 digits for debugging
                        obj[key] = f"***{value[-4:]}"
                elif key == "name":
                    obj[key] = "[REDACTED]"
                elif key == "body" and isinstance(value, str):
                    # Apply PII filter to message text
                    obj[key] = _pii_filter._mask_sensitive(value)
                elif isinstance(value, (dict, list)):
                    redact_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                redact_recursive(item)

    redact_recursive(sanitized)
    return sanitized


async def verify_whatsapp_signature(request: Request) -> bool:
    """
    Verify WhatsApp webhook signature using X-Hub-Signature-256 header.

    The signature is calculated as HMAC-SHA256 of the raw request body
    using the app secret as the key.

    In development: Skip verification if app_secret not configured
    In production: Always require valid signature

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid or verification is skipped
    """
    adapter = WhatsAppAdapter()

    # In development, skip verification if app_secret not configured
    if settings.environment != "production" and not adapter.app_secret:
        logger.debug("WhatsApp webhook signature verification skipped (not configured in dev)")
        return True

    # Get the signature from header
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        logger.warning(
            f"WhatsApp webhook request without signature from "
            f"{request.client.host if request.client else 'unknown'}"
        )
        return False

    # Get raw body for signature verification
    body = await request.body()

    if not adapter.verify_signature(body, signature):
        logger.warning(
            f"Invalid WhatsApp webhook signature from "
            f"{request.client.host if request.client else 'unknown'}"
        )
        return False

    return True


@router.get("/webhook")
@limiter.limit("100/minute")  # Verification endpoint (called once per subscription)
async def verify_webhook(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    """
    WhatsApp webhook verification endpoint (GET).

    This endpoint is called by WhatsApp when you configure a webhook.
    It verifies that you control the endpoint by checking the verify_token
    and echoing back the challenge.

    Query Parameters (from WhatsApp):
        hub.mode: Should be "subscribe"
        hub.verify_token: Must match your configured WHATSAPP_VERIFY_TOKEN
        hub.challenge: String to echo back if verification succeeds

    Returns:
        The challenge string as plain text if verification succeeds

    Raises:
        HTTPException 403: If verification fails
    """
    logger.info(
        f"WhatsApp webhook verification request: mode={hub_mode}, "
        f"has_token={bool(hub_verify_token)}, has_challenge={bool(hub_challenge)}"
    )

    adapter = WhatsAppAdapter()
    challenge = adapter.verify_webhook(
        mode=hub_mode or "",
        token=hub_verify_token or "",
        challenge=hub_challenge or "",
    )

    if challenge:
        # Must return challenge as plain text, not JSON
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed"
    )


@router.post("/webhook")
@limiter.limit("100/minute")  # Public endpoint (called by WhatsApp servers)
async def whatsapp_webhook(request: Request) -> Dict[str, Any]:
    """
    WhatsApp webhook endpoint (POST).

    This endpoint is PUBLIC (no API key required) as it's called by WhatsApp servers.
    Security is provided by webhook signature verification using the app secret.

    This endpoint receives:
    1. Message notifications (new messages from users)
    2. Status updates (sent, delivered, read)
    3. Error notifications

    Flow:
    1. Verifies the webhook signature (in production)
    2. Parses the WhatsApp webhook payload
    3. Extracts messages and converts to standard ingest format
    4. Calls the /ingest-message endpoint
    5. Sends the response back to the user via WhatsApp

    Args:
        request: FastAPI request with WhatsApp webhook payload

    Returns:
        Success response (WhatsApp expects HTTP 200)

    Raises:
        HTTPException 403: If webhook signature verification fails
    """
    # Verify WhatsApp webhook signature
    if not await verify_whatsapp_signature(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )

    try:
        # Get WhatsApp webhook payload
        payload = await request.json()

        # Log and persist with PII redaction
        redacted_payload = _redact_pii_from_webhook(payload)
        logger.info(f"Received WhatsApp webhook: {json.dumps(redacted_payload)[:500]}...")

        try:
            _WEBHOOK_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _WEBHOOK_DUMP_PATH.open("a", encoding="utf-8") as f:
                # Write redacted version to prevent PII in logs
                f.write(json.dumps(redacted_payload, ensure_ascii=True) + "\n")
        except Exception as dump_error:
            logger.warning(f"Failed to persist webhook payload: {dump_error}")

        # Initialize WhatsApp adapter
        adapter = WhatsAppAdapter()

        # Parse messages from webhook
        parsed_messages = adapter.parse_webhook_payload(payload)

        if not parsed_messages:
            # Could be a status update or empty notification
            status_updates = adapter.parse_status_updates(payload)
            if status_updates:
                logger.info(f"Received {len(status_updates)} status updates")
                for status_update in status_updates:
                    logger.debug(
                        f"Message {status_update.id} status: {status_update.status}"
                    )
            else:
                logger.debug("Received webhook without messages or status updates")

            return {"status": "ok", "message": "No messages to process"}

        # Process each message
        processed_count = 0
        for parsed in parsed_messages:
            try:
                # SANITIZE INPUTS from WhatsApp
                text = sanitize_text(parsed.text, max_length=4000)
                external_user_id = sanitize_identifier(parsed.external_user_id)

                # Sanitize company_id if present in metadata
                company_id = parsed.metadata.get("company_id")
                if company_id:
                    company_id = sanitize_company_id(company_id)

                # Create ingest message request
                ingest_request = IngestMessageRequest(
                    channel=IngestChannel.WHATSAPP,
                    external_user_id=external_user_id,
                    text=text,
                    metadata={
                        **parsed.metadata,
                        "sender_name": parsed.sender_name,
                        "message_type": parsed.message_type.value,
                        "media_id": parsed.media_id,
                        "is_reply": parsed.is_reply,
                        "reply_to_message_id": parsed.reply_to_message_id,
                    },
                    company_id=company_id
                )

                # Process the message through the ingest endpoint
                logger.info(f"Processing WhatsApp message from {parsed.wa_id}")
                response = await ingest_message(ingest_request)
                logger.info(
                    f"Processed message: ticket_id={response.ticket_id}, "
                    f"escalated={response.escalated}"
                )

                # Send the reply back to WhatsApp
                if response.reply_text:
                    try:
                        await adapter.send_message(
                            to=parsed.wa_id,
                            text=response.reply_text,
                        )
                        logger.debug(f"Sent reply to {parsed.wa_id}")
                    except Exception as send_error:
                        logger.error(
                            f"Failed to send reply to {parsed.wa_id}: {send_error}"
                        )

                # Mark message as read
                try:
                    await adapter.mark_as_read(parsed.message_id)
                except Exception as read_error:
                    logger.debug(f"Failed to mark message as read: {read_error}")

                processed_count += 1

            except ValueError as e:
                logger.warning(f"Input validation failed for WhatsApp message: {e}")
                continue
            except Exception as e:
                logger.error(
                    f"Error processing WhatsApp message {parsed.message_id}: {e}",
                    exc_info=True
                )
                continue

        logger.info(f"Processed {processed_count}/{len(parsed_messages)} WhatsApp messages")

        return {
            "status": "ok",
            "message": f"Processed {processed_count} messages",
            "processed": processed_count,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}", exc_info=True)
        # Return 200 to prevent WhatsApp from retrying
        # Log the error for investigation
        return {
            "status": "error",
            "message": "Internal error processing webhook",
        }


@router.post("/send")
@limiter.limit("30/minute")  # Admin endpoint
async def send_message(
    request: Request,
    to: str = Query(..., description="Recipient's WhatsApp ID (phone number without +)"),
    text: str = Query(..., description="Message text"),
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Send a text message via WhatsApp.

    Requires: X-API-Key header

    Args:
        to: Recipient's WhatsApp ID (e.g., "5511999999999")
        text: Message text
        api_key: Authenticated API key (auto-injected)

    Returns:
        Response from WhatsApp API
    """
    try:
        # Sanitize input
        text = sanitize_text(text, max_length=4096)

        adapter = WhatsAppAdapter()
        result = await adapter.send_message(to=to, text=text)

        logger.info(f"Sent WhatsApp message to {to[:4]}***")
        return result

    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message. Please check the recipient and try again."
        )


@router.post("/send/template")
@limiter.limit("30/minute")  # Admin endpoint
async def send_template_message(
    request: Request,
    to: str = Query(..., description="Recipient's WhatsApp ID"),
    template_name: str = Query(..., description="Template name"),
    language_code: str = Query("en_US", description="Language code"),
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Send a template message via WhatsApp.

    Template messages are pre-approved message formats that can be sent
    to users who haven't messaged you in the last 24 hours.

    Requires: X-API-Key header

    Args:
        to: Recipient's WhatsApp ID
        template_name: Name of the approved template
        language_code: Language code (e.g., "en_US", "pt_BR")
        api_key: Authenticated API key (auto-injected)

    Returns:
        Response from WhatsApp API
    """
    try:
        adapter = WhatsAppAdapter()
        result = await adapter.send_template(
            to=to,
            template_name=template_name,
            language_code=language_code,
        )

        logger.info(f"Sent WhatsApp template '{template_name}' to {to[:4]}***")
        return result

    except Exception as e:
        logger.error(f"Failed to send WhatsApp template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send template message. Please verify the template name and try again."
        )


@router.get("/business-profile")
@limiter.limit("30/minute")  # Admin endpoint
async def get_business_profile(
    request: Request,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get WhatsApp Business profile information.

    Requires: X-API-Key header

    Args:
        api_key: Authenticated API key (auto-injected)

    Returns:
        Business profile data
    """
    try:
        adapter = WhatsAppAdapter()
        profile = await adapter.get_business_profile()
        return profile

    except Exception as e:
        logger.error(f"Failed to get WhatsApp business profile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get business profile"
        )


@router.post("/mark-read")
@limiter.limit("60/minute")  # Admin endpoint
async def mark_message_read(
    request: Request,
    message_id: str = Query(..., description="Message ID to mark as read"),
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Mark a WhatsApp message as read.

    Requires: X-API-Key header

    Args:
        message_id: ID of the message to mark as read
        api_key: Authenticated API key (auto-injected)

    Returns:
        Response from WhatsApp API
    """
    try:
        adapter = WhatsAppAdapter()
        result = await adapter.mark_as_read(message_id)
        return result

    except Exception as e:
        logger.error(f"Failed to mark message as read: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark message as read"
        )


@router.get("/media/{media_id}")
@limiter.limit("30/minute")  # Admin endpoint
async def get_media_url(
    request: Request,
    media_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get the download URL for a WhatsApp media file.

    The URL is temporary and valid for approximately 5 minutes.

    Requires: X-API-Key header

    Args:
        media_id: Media ID from received message
        api_key: Authenticated API key (auto-injected)

    Returns:
        Object containing the temporary download URL
    """
    try:
        adapter = WhatsAppAdapter()
        url = await adapter.get_media_url(media_id)
        return {"media_id": media_id, "url": url}

    except Exception as e:
        logger.error(f"Failed to get media URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get media URL"
        )
