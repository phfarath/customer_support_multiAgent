"""
WhatsApp Business API adapter for handling webhooks and sending messages

Based on WhatsApp Cloud API documentation:
https://developers.facebook.com/docs/whatsapp/cloud-api/
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import hashlib
import hmac

from src.config import settings
from src.utils.http_client import get_http_client
from src.models.whatsapp import (
    WhatsAppWebhookPayload,
    WhatsAppMessage,
    WhatsAppMessageType,
    WhatsAppParsedMessage,
    WhatsAppStatusUpdate,
)

logger = logging.getLogger(__name__)


class WhatsAppAdapter:
    """
    Adapter for WhatsApp Business Cloud API integration.

    Handles:
    - Webhook verification (GET)
    - Incoming message parsing
    - Message status updates
    - Sending text/media messages
    - Media download

    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/
    """

    # WhatsApp Cloud API base URL
    API_BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        verify_token: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        """
        Initialize the WhatsApp adapter.

        Args:
            access_token: WhatsApp Business API access token
            phone_number_id: WhatsApp Business phone number ID
            verify_token: Token for webhook verification
            app_secret: App secret for signature verification
        """
        self.access_token = access_token or getattr(settings, "whatsapp_access_token", None)
        self.phone_number_id = phone_number_id or getattr(settings, "whatsapp_phone_number_id", None)
        self.verify_token = verify_token or getattr(settings, "whatsapp_verify_token", None)
        self.app_secret = app_secret or getattr(settings, "whatsapp_app_secret", None)

        self.api_url = f"{self.API_BASE_URL}/{self.phone_number_id}"

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    # ========================================
    # Webhook Verification
    # ========================================

    def verify_webhook(
        self,
        mode: str,
        token: str,
        challenge: str,
    ) -> Optional[str]:
        """
        Verify webhook subscription request from WhatsApp.

        Args:
            mode: Should be "subscribe"
            token: Verification token (must match self.verify_token)
            challenge: Challenge string to return

        Returns:
            Challenge string if verification succeeds, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("WhatsApp webhook verification successful")
            return challenge

        logger.warning(
            f"WhatsApp webhook verification failed: mode={mode}, "
            f"token_match={token == self.verify_token}"
        )
        return None

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using app secret.

        Args:
            payload: Raw request body bytes
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.app_secret:
            logger.warning("WhatsApp app_secret not configured, skipping signature verification")
            return True  # Skip in development

        if not signature:
            logger.warning("No signature provided in webhook request")
            return False

        # Signature format: "sha256=<hex_digest>"
        if not signature.startswith("sha256="):
            logger.warning(f"Invalid signature format: {signature[:20]}...")
            return False

        expected_signature = signature[7:]  # Remove "sha256=" prefix

        # Calculate HMAC-SHA256
        computed_hash = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, expected_signature):
            logger.warning("WhatsApp webhook signature verification failed")
            return False

        return True

    # ========================================
    # Message Parsing
    # ========================================

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> List[WhatsAppParsedMessage]:
        """
        Parse WhatsApp webhook payload and extract messages.

        Args:
            payload: Raw webhook payload from WhatsApp

        Returns:
            List of parsed messages ready for processing
        """
        parsed_messages: List[WhatsAppParsedMessage] = []

        try:
            webhook_data = WhatsAppWebhookPayload(**payload)
        except Exception as e:
            logger.error(f"Failed to parse WhatsApp webhook payload: {e}")
            return parsed_messages

        for entry in webhook_data.entry:
            for change in entry.changes:
                value = change.value
                phone_number_id = value.metadata.phone_number_id

                # Get contacts for name lookup
                contacts_map: Dict[str, str] = {}
                if value.contacts:
                    for contact in value.contacts:
                        contacts_map[contact.wa_id] = contact.profile.name

                # Process messages
                if value.messages:
                    for message in value.messages:
                        parsed = self._parse_single_message(
                            message=message,
                            phone_number_id=phone_number_id,
                            sender_name=contacts_map.get(message.from_),
                        )
                        if parsed:
                            parsed_messages.append(parsed)

        return parsed_messages

    def _parse_single_message(
        self,
        message: WhatsAppMessage,
        phone_number_id: str,
        sender_name: Optional[str] = None,
    ) -> Optional[WhatsAppParsedMessage]:
        """
        Parse a single WhatsApp message into normalized format.

        Args:
            message: WhatsApp message object
            phone_number_id: Business phone number ID
            sender_name: Sender's name from contacts

        Returns:
            Parsed message or None if message type is not supported
        """
        text = ""
        media_id = None
        message_type = message.type

        # Extract text based on message type
        if message.type == WhatsAppMessageType.TEXT and message.text:
            text = message.text.body

        elif message.type == WhatsAppMessageType.IMAGE and message.image:
            text = message.image.caption or "[Image]"
            media_id = message.image.id

        elif message.type == WhatsAppMessageType.AUDIO and message.audio:
            text = "[Audio message]"
            media_id = message.audio.id

        elif message.type == WhatsAppMessageType.VIDEO and message.video:
            text = message.video.caption or "[Video]"
            media_id = message.video.id

        elif message.type == WhatsAppMessageType.DOCUMENT and message.document:
            filename = message.document.filename or "document"
            text = message.document.caption or f"[Document: {filename}]"
            media_id = message.document.id

        elif message.type == WhatsAppMessageType.STICKER and message.sticker:
            text = "[Sticker]"
            media_id = message.sticker.id

        elif message.type == WhatsAppMessageType.LOCATION and message.location:
            loc = message.location
            text = f"[Location: {loc.name or 'Pin'} - {loc.latitude}, {loc.longitude}]"
            if loc.address:
                text = f"[Location: {loc.name or 'Pin'} - {loc.address}]"

        elif message.type == WhatsAppMessageType.INTERACTIVE and message.interactive:
            interactive = message.interactive
            if interactive.type == "button_reply" and interactive.button_reply:
                text = interactive.button_reply.get("title", "")
            elif interactive.type == "list_reply" and interactive.list_reply:
                text = interactive.list_reply.get("title", "")
            else:
                text = "[Interactive response]"

        elif message.type == WhatsAppMessageType.BUTTON and message.button:
            text = message.button.text

        elif message.type == WhatsAppMessageType.REACTION and message.reaction:
            # Reactions are typically handled differently (not as new messages)
            logger.debug(f"Received reaction: {message.reaction.emoji} on {message.reaction.message_id}")
            return None

        else:
            logger.warning(f"Unsupported WhatsApp message type: {message.type}")
            text = f"[Unsupported message type: {message.type}]"
            message_type = WhatsAppMessageType.UNKNOWN

        if not text:
            return None

        # Check if this is a reply to another message
        is_reply = message.context is not None
        reply_to_message_id = message.context.get("id") if message.context else None

        # Parse timestamp
        try:
            timestamp = datetime.fromtimestamp(int(message.timestamp))
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

        return WhatsAppParsedMessage(
            external_user_id=f"whatsapp:{message.from_}",
            text=text,
            message_type=message_type,
            message_id=message.id,
            wa_id=message.from_,
            phone_number_id=phone_number_id,
            timestamp=timestamp,
            sender_name=sender_name,
            media_id=media_id,
            is_reply=is_reply,
            reply_to_message_id=reply_to_message_id,
            metadata={
                "message_id": message.id,
                "wa_id": message.from_,
                "phone_number_id": phone_number_id,
                "sender_name": sender_name,
                "message_type": message_type.value,
                "timestamp": timestamp.isoformat(),
            },
        )

    def parse_status_updates(self, payload: Dict[str, Any]) -> List[WhatsAppStatusUpdate]:
        """
        Parse status updates from webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            List of status updates
        """
        status_updates: List[WhatsAppStatusUpdate] = []

        try:
            webhook_data = WhatsAppWebhookPayload(**payload)
        except Exception as e:
            logger.error(f"Failed to parse WhatsApp webhook payload for statuses: {e}")
            return status_updates

        for entry in webhook_data.entry:
            for change in entry.changes:
                if change.value.statuses:
                    status_updates.extend(change.value.statuses)

        return status_updates

    # ========================================
    # Sending Messages
    # ========================================

    async def send_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.

        Args:
            to: Recipient's WhatsApp ID (phone number without +)
            text: Message text
            preview_url: Whether to show URL previews

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url,
            },
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_image(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_id: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an image message.

        Args:
            to: Recipient's WhatsApp ID
            image_url: Public URL of the image (mutually exclusive with image_id)
            image_id: Media ID of uploaded image (mutually exclusive with image_url)
            caption: Optional caption

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        image_content: Dict[str, Any] = {}
        if image_url:
            image_content["link"] = image_url
        elif image_id:
            image_content["id"] = image_id
        else:
            raise ValueError("Either image_url or image_id must be provided")

        if caption:
            image_content["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_content,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_document(
        self,
        to: str,
        document_url: Optional[str] = None,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a document message.

        Args:
            to: Recipient's WhatsApp ID
            document_url: Public URL of the document
            document_id: Media ID of uploaded document
            filename: Filename to display
            caption: Optional caption

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        doc_content: Dict[str, Any] = {}
        if document_url:
            doc_content["link"] = document_url
        elif document_id:
            doc_content["id"] = document_id
        else:
            raise ValueError("Either document_url or document_id must be provided")

        if filename:
            doc_content["filename"] = filename
        if caption:
            doc_content["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": doc_content,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a template message.

        Args:
            to: Recipient's WhatsApp ID
            template_name: Name of the approved template
            language_code: Language code (e.g., "en_US", "pt_BR")
            components: Template components (header, body, buttons)

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        template: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_interactive_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons (max 3 buttons).

        Args:
            to: Recipient's WhatsApp ID
            body_text: Main message body
            buttons: List of buttons [{"id": "...", "title": "..."}]
            header_text: Optional header
            footer_text: Optional footer

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        interactive: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": btn} for btn in buttons[:3]  # Max 3 buttons
                ]
            },
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_interactive_list(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive list message.

        Args:
            to: Recipient's WhatsApp ID
            body_text: Main message body
            button_text: Text on the list button
            sections: List sections with rows
            header_text: Optional header
            footer_text: Optional footer

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        interactive: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def send_reaction(
        self,
        to: str,
        message_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Send a reaction to a message.

        Args:
            to: Recipient's WhatsApp ID
            message_id: ID of the message to react to
            emoji: Emoji to react with

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji,
            },
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.

        Args:
            message_id: ID of the message to mark as read

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    # ========================================
    # Media Handling
    # ========================================

    async def get_media_url(self, media_id: str) -> str:
        """
        Get the download URL for a media file.

        Args:
            media_id: Media ID from received message

        Returns:
            Temporary download URL (valid for 5 minutes)
        """
        url = f"{self.API_BASE_URL}/{media_id}"

        client = get_http_client()
        response = await client.get(url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        return data.get("url", "")

    async def download_media(self, media_url: str) -> bytes:
        """
        Download media file from WhatsApp.

        Args:
            media_url: URL from get_media_url()

        Returns:
            Media file bytes
        """
        client = get_http_client()
        response = await client.get(media_url, headers=self._get_headers())
        response.raise_for_status()
        return response.content

    async def upload_media(
        self,
        file_data: bytes,
        mime_type: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        Upload media to WhatsApp for later use.

        Args:
            file_data: File content as bytes
            mime_type: MIME type (e.g., "image/jpeg", "application/pdf")
            filename: Optional filename

        Returns:
            Media ID for use in send_* methods
        """
        url = f"{self.api_url}/media"

        # WhatsApp requires multipart/form-data for uploads
        files = {
            "file": (filename or "file", file_data, mime_type),
        }
        data = {
            "messaging_product": "whatsapp",
            "type": mime_type,
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        client = get_http_client()
        response = await client.post(url, data=data, files=files, headers=headers)
        response.raise_for_status()

        result = response.json()
        return result.get("id", "")

    # ========================================
    # Business Profile
    # ========================================

    async def get_business_profile(self) -> Dict[str, Any]:
        """
        Get the business profile information.

        Returns:
            Business profile data
        """
        url = f"{self.api_url}/whatsapp_business_profile"
        params = {"fields": "about,address,description,email,profile_picture_url,websites,vertical"}

        client = get_http_client()
        response = await client.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def update_business_profile(
        self,
        about: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        email: Optional[str] = None,
        websites: Optional[List[str]] = None,
        vertical: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the business profile.

        Args:
            about: Short description (max 139 chars)
            address: Business address
            description: Longer description (max 512 chars)
            email: Business email
            websites: List of website URLs (max 2)
            vertical: Business category

        Returns:
            Response from WhatsApp API
        """
        url = f"{self.api_url}/whatsapp_business_profile"

        payload: Dict[str, Any] = {"messaging_product": "whatsapp"}

        if about is not None:
            payload["about"] = about[:139]
        if address is not None:
            payload["address"] = address
        if description is not None:
            payload["description"] = description[:512]
        if email is not None:
            payload["email"] = email
        if websites is not None:
            payload["websites"] = websites[:2]
        if vertical is not None:
            payload["vertical"] = vertical

        client = get_http_client()
        response = await client.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
