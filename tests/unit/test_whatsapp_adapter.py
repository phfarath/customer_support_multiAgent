"""
Unit tests for WhatsApp Business API adapter

Tests cover:
- Webhook verification
- Signature verification
- Message parsing (various types)
- Outgoing message formatting
"""
import pytest
import hashlib
import hmac
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.adapters.whatsapp_adapter import WhatsAppAdapter
from src.models.whatsapp import (
    WhatsAppMessageType,
    WhatsAppParsedMessage,
    WhatsAppStatusUpdate,
    WhatsAppMessageStatus,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def adapter():
    """Create a WhatsApp adapter for testing."""
    return WhatsAppAdapter(
        access_token="test_access_token",
        phone_number_id="123456789",
        verify_token="test_verify_token",
        app_secret="test_app_secret",
    )


@pytest.fixture
def sample_text_message_payload():
    """Sample webhook payload with a text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "John Doe"},
                                    "wa_id": "5511999999999"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5511999999999",
                                    "id": "wamid.HBgNNTUxMTk5OTk5OTk5OQ",
                                    "timestamp": "1704067200",
                                    "text": {"body": "Hello, I need help!"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_image_message_payload():
    """Sample webhook payload with an image message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Jane Doe"},
                                    "wa_id": "5511888888888"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5511888888888",
                                    "id": "wamid.HBgNNTUxMTg4ODg4ODg4OA",
                                    "timestamp": "1704067200",
                                    "type": "image",
                                    "image": {
                                        "caption": "Check this out",
                                        "mime_type": "image/jpeg",
                                        "sha256": "abc123",
                                        "id": "media_id_123"
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_status_update_payload():
    """Sample webhook payload with a status update."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789"
                            },
                            "statuses": [
                                {
                                    "id": "wamid.HBgNNTUxMTk5OTk5OTk5OQ",
                                    "status": "delivered",
                                    "timestamp": "1704067200",
                                    "recipient_id": "5511999999999"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_interactive_button_payload():
    """Sample webhook payload with interactive button response."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "123456789"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "User"},
                                    "wa_id": "5511777777777"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5511777777777",
                                    "id": "wamid.interactive",
                                    "timestamp": "1704067200",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "btn_confirm",
                                            "title": "Confirm Order"
                                        }
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


# ============================================================
# Webhook Verification Tests
# ============================================================

class TestWebhookVerification:
    """Tests for webhook verification."""

    def test_verify_webhook_success(self, adapter):
        """Test successful webhook verification."""
        result = adapter.verify_webhook(
            mode="subscribe",
            token="test_verify_token",
            challenge="challenge_123"
        )
        assert result == "challenge_123"

    def test_verify_webhook_wrong_mode(self, adapter):
        """Test webhook verification with wrong mode."""
        result = adapter.verify_webhook(
            mode="unsubscribe",
            token="test_verify_token",
            challenge="challenge_123"
        )
        assert result is None

    def test_verify_webhook_wrong_token(self, adapter):
        """Test webhook verification with wrong token."""
        result = adapter.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="challenge_123"
        )
        assert result is None

    def test_verify_webhook_empty_values(self, adapter):
        """Test webhook verification with empty values."""
        result = adapter.verify_webhook(
            mode="",
            token="",
            challenge=""
        )
        assert result is None


class TestSignatureVerification:
    """Tests for webhook signature verification."""

    def test_verify_signature_success(self, adapter):
        """Test successful signature verification."""
        payload = b'{"test": "data"}'
        expected_hash = hmac.new(
            b"test_app_secret",
            payload,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_hash}"

        result = adapter.verify_signature(payload, signature)
        assert result is True

    def test_verify_signature_wrong_signature(self, adapter):
        """Test signature verification with wrong signature."""
        payload = b'{"test": "data"}'
        signature = "sha256=wronghash123"

        result = adapter.verify_signature(payload, signature)
        assert result is False

    def test_verify_signature_invalid_format(self, adapter):
        """Test signature verification with invalid format."""
        payload = b'{"test": "data"}'
        signature = "invalid_format"

        result = adapter.verify_signature(payload, signature)
        assert result is False

    def test_verify_signature_empty_signature(self, adapter):
        """Test signature verification with empty signature."""
        payload = b'{"test": "data"}'

        result = adapter.verify_signature(payload, "")
        assert result is False

    def test_verify_signature_no_app_secret(self):
        """Test signature verification skipped when no app_secret."""
        adapter = WhatsAppAdapter(
            access_token="token",
            phone_number_id="123",
            app_secret=None,
        )
        payload = b'{"test": "data"}'

        result = adapter.verify_signature(payload, "any_signature")
        assert result is True  # Skipped


# ============================================================
# Message Parsing Tests
# ============================================================

class TestMessageParsing:
    """Tests for parsing incoming messages."""

    def test_parse_text_message(self, adapter, sample_text_message_payload):
        """Test parsing a text message."""
        messages = adapter.parse_webhook_payload(sample_text_message_payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.external_user_id == "whatsapp:5511999999999"
        assert msg.text == "Hello, I need help!"
        assert msg.message_type == WhatsAppMessageType.TEXT
        assert msg.wa_id == "5511999999999"
        assert msg.sender_name == "John Doe"
        assert msg.message_id == "wamid.HBgNNTUxMTk5OTk5OTk5OQ"

    def test_parse_image_message(self, adapter, sample_image_message_payload):
        """Test parsing an image message."""
        messages = adapter.parse_webhook_payload(sample_image_message_payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.external_user_id == "whatsapp:5511888888888"
        assert msg.text == "Check this out"
        assert msg.message_type == WhatsAppMessageType.IMAGE
        assert msg.media_id == "media_id_123"
        assert msg.sender_name == "Jane Doe"

    def test_parse_interactive_button(self, adapter, sample_interactive_button_payload):
        """Test parsing an interactive button response."""
        messages = adapter.parse_webhook_payload(sample_interactive_button_payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.text == "Confirm Order"
        assert msg.message_type == WhatsAppMessageType.INTERACTIVE

    def test_parse_status_updates(self, adapter, sample_status_update_payload):
        """Test parsing status updates."""
        statuses = adapter.parse_status_updates(sample_status_update_payload)

        assert len(statuses) == 1
        status = statuses[0]
        assert status.id == "wamid.HBgNNTUxMTk5OTk5OTk5OQ"
        assert status.status == WhatsAppMessageStatus.DELIVERED
        assert status.recipient_id == "5511999999999"

    def test_parse_empty_payload(self, adapter):
        """Test parsing empty/invalid payload."""
        messages = adapter.parse_webhook_payload({})
        assert len(messages) == 0

    def test_parse_payload_no_messages(self, adapter):
        """Test parsing payload without messages."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "123456789"
                                }
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        messages = adapter.parse_webhook_payload(payload)
        assert len(messages) == 0

    def test_parse_location_message(self, adapter):
        """Test parsing a location message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "123456789"
                                },
                                "contacts": [
                                    {"profile": {"name": "User"}, "wa_id": "5511999999999"}
                                ],
                                "messages": [
                                    {
                                        "from": "5511999999999",
                                        "id": "wamid.location",
                                        "timestamp": "1704067200",
                                        "type": "location",
                                        "location": {
                                            "latitude": -23.5505,
                                            "longitude": -46.6333,
                                            "name": "Sao Paulo",
                                            "address": "Av. Paulista, 1000"
                                        }
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        messages = adapter.parse_webhook_payload(payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == WhatsAppMessageType.LOCATION
        assert "Sao Paulo" in msg.text
        assert "Av. Paulista, 1000" in msg.text

    def test_parse_document_message(self, adapter):
        """Test parsing a document message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "123456789"
                                },
                                "contacts": [
                                    {"profile": {"name": "User"}, "wa_id": "5511999999999"}
                                ],
                                "messages": [
                                    {
                                        "from": "5511999999999",
                                        "id": "wamid.document",
                                        "timestamp": "1704067200",
                                        "type": "document",
                                        "document": {
                                            "id": "doc_123",
                                            "filename": "invoice.pdf",
                                            "mime_type": "application/pdf"
                                        }
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        messages = adapter.parse_webhook_payload(payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.message_type == WhatsAppMessageType.DOCUMENT
        assert "invoice.pdf" in msg.text
        assert msg.media_id == "doc_123"

    def test_parse_reply_message(self, adapter):
        """Test parsing a reply to another message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "123456789"
                                },
                                "contacts": [
                                    {"profile": {"name": "User"}, "wa_id": "5511999999999"}
                                ],
                                "messages": [
                                    {
                                        "from": "5511999999999",
                                        "id": "wamid.reply",
                                        "timestamp": "1704067200",
                                        "type": "text",
                                        "text": {"body": "This is a reply"},
                                        "context": {
                                            "from": "15551234567",
                                            "id": "wamid.original"
                                        }
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        messages = adapter.parse_webhook_payload(payload)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.is_reply is True
        assert msg.reply_to_message_id == "wamid.original"


# ============================================================
# Send Message Tests
# ============================================================

class TestSendMessages:
    """Tests for sending messages."""

    @pytest.mark.asyncio
    async def test_send_text_message(self, adapter):
        """Test sending a text message."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
                "messages": [{"id": "wamid.response"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.send_message(
                to="5511999999999",
                text="Hello from test!"
            )

            assert result["messaging_product"] == "whatsapp"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "Hello from test!" in str(call_args)

    @pytest.mark.asyncio
    async def test_send_template_message(self, adapter):
        """Test sending a template message."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
                "messages": [{"id": "wamid.template"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.send_template(
                to="5511999999999",
                template_name="hello_world",
                language_code="en_US"
            )

            assert result["messaging_product"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_send_interactive_buttons(self, adapter):
        """Test sending interactive buttons."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
                "messages": [{"id": "wamid.interactive"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.send_interactive_buttons(
                to="5511999999999",
                body_text="Please choose an option:",
                buttons=[
                    {"id": "btn1", "title": "Option 1"},
                    {"id": "btn2", "title": "Option 2"},
                ],
                header_text="Menu",
                footer_text="Reply to select"
            )

            assert result["messaging_product"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_send_image(self, adapter):
        """Test sending an image."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "5511999999999", "wa_id": "5511999999999"}],
                "messages": [{"id": "wamid.image"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.send_image(
                to="5511999999999",
                image_url="https://example.com/image.jpg",
                caption="Check this image"
            )

            assert result["messaging_product"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_send_image_requires_url_or_id(self, adapter):
        """Test that send_image requires either URL or ID."""
        with pytest.raises(ValueError, match="Either image_url or image_id"):
            await adapter.send_image(to="5511999999999")


# ============================================================
# Mark As Read Tests
# ============================================================

class TestMarkAsRead:
    """Tests for marking messages as read."""

    @pytest.mark.asyncio
    async def test_mark_as_read(self, adapter):
        """Test marking a message as read."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.mark_as_read("wamid.test123")

            assert result["success"] is True
            call_args = mock_client.post.call_args
            assert "read" in str(call_args)


# ============================================================
# Media Handling Tests
# ============================================================

class TestMediaHandling:
    """Tests for media operations."""

    @pytest.mark.asyncio
    async def test_get_media_url(self, adapter):
        """Test getting media download URL."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "url": "https://lookaside.fbsbx.com/media/file.jpg"
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            url = await adapter.get_media_url("media_123")

            assert "lookaside.fbsbx.com" in url

    @pytest.mark.asyncio
    async def test_download_media(self, adapter):
        """Test downloading media content."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = b"fake_image_bytes"
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            content = await adapter.download_media("https://example.com/media.jpg")

            assert content == b"fake_image_bytes"


# ============================================================
# Business Profile Tests
# ============================================================

class TestBusinessProfile:
    """Tests for business profile operations."""

    @pytest.mark.asyncio
    async def test_get_business_profile(self, adapter):
        """Test getting business profile."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{
                    "about": "Test Business",
                    "description": "Test Description"
                }]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            profile = await adapter.get_business_profile()

            assert "data" in profile

    @pytest.mark.asyncio
    async def test_update_business_profile(self, adapter):
        """Test updating business profile."""
        with patch("src.adapters.whatsapp_adapter.get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": True}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await adapter.update_business_profile(
                about="Updated About",
                description="Updated Description"
            )

            assert result["success"] is True
