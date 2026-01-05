# Telegram Bot Integration Setup

This guide explains how to set up and configure the Telegram bot for the MultiAgent Customer Support System.

## Overview

The Telegram integration follows a channel-agnostic architecture:
- **Backend API**: Central endpoint `/api/ingest-message` that processes messages from any channel
- **Telegram Adapter**: Handles Telegram-specific webhook parsing and message sending
- **Telegram Webhook**: `/telegram/webhook` endpoint receives updates from Telegram

## Architecture

```
Telegram User → Telegram Bot API → /telegram/webhook → /api/ingest-message → Agent Pipeline → Response
```

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat with BotFather
3. Send `/newbot` command
4. Follow the prompts to:
   - Choose a name for your bot
   - Choose a username (must end in `bot`)
5. BotFather will provide you with a **Bot Token** (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Configure Environment Variables

Add the Telegram bot token to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

You can copy the `.env.example` file and update it:

```bash
cp .env.example .env
```

## Step 3: Expose Your Backend Publicly

For Telegram to send webhook updates to your backend, it must be publicly accessible. You have several options:

### Option A: Ngrok (Recommended for Development)

1. Install ngrok: https://ngrok.com/download
2. Start your backend server:
   ```bash
   python main.py
   ```
3. In another terminal, expose port 8000:
   ```bash
   ngrok http 8000
   ```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Option B: Public Server

Deploy your backend to a cloud provider (AWS, GCP, Azure, Railway, Render, etc.) with a public domain.

## Step 4: Set Up the Webhook

Use the provided API endpoint to set the webhook:

```bash
curl -X POST "http://localhost:8000/telegram/webhook/set?webhook_url=https://your-domain.com/telegram/webhook"
```

Or test with ngrok:
```bash
curl -X POST "http://localhost:8000/telegram/webhook/set?webhook_url=https://abc123.ngrok.io/telegram/webhook"
```

### Verify Webhook

```bash
curl "http://localhost:8000/telegram/webhook/info"
```

## Step 5: Test the Bot

1. Open Telegram and search for your bot by username
2. Start a chat with the bot
3. Send a message (e.g., "Hello, I need help with my order")
4. The bot should respond with an automated message from the agent pipeline

## API Endpoints

### Telegram Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telegram/webhook` | POST | Receives updates from Telegram |
| `/telegram/webhook/info` | GET | Get current webhook information |
| `/telegram/webhook/set` | POST | Set webhook URL |
| `/telegram/webhook/delete` | POST | Delete webhook |
| `/telegram/bot/info` | GET | Get bot information |

### Ingest Message Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest-message` | POST | Channel-agnostic message ingestion |

### Example Ingest Message Request

```bash
curl -X POST "http://localhost:8000/api/ingest-message" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "external_user_id": "telegram:123456789",
    "text": "I need help with my order"
  }'
```

## Troubleshooting

### Webhook Not Receiving Updates

1. Check if webhook is set correctly:
   ```bash
   curl "http://localhost:8000/telegram/webhook/info"
   ```
2. Verify your backend is publicly accessible
3. Check backend logs for errors

### Bot Not Responding

1. Check backend logs for errors
2. Verify MongoDB connection
3. Verify OpenAI API key is set
4. Check ticket creation in MongoDB

### Common Errors

- **409 Conflict**: Webhook already set. Delete it first:
  ```bash
  curl -X POST "http://localhost:8000/telegram/webhook/delete"
  ```

- **Bad Request**: Invalid webhook URL. Ensure it's a valid HTTPS URL.

## Data Flow

1. **User sends message** to Telegram bot
2. **Telegram sends webhook** to `/telegram/webhook`
3. **Adapter parses** the Telegram update payload
4. **Ingest endpoint** creates/updates ticket and runs agent pipeline
5. **Agent pipeline** generates response
6. **Adapter sends** response back to Telegram user

## Database Schema

### Tickets Collection

```json
{
  "ticket_id": "telegram:123456789_1234567890.123",
  "customer_id": "telegram:123456789",
  "channel": "telegram",
  "external_user_id": "telegram:123456789",
  "subject": "I need help with my order...",
  "description": "I need help with my order",
  "priority": "P3",
  "status": "in_progress",
  "current_phase": "triage",
  "interactions_count": 2,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "lock_version": 0
}
```

### Interactions Collection

```json
{
  "ticket_id": "telegram:123456789_1234567890.123",
  "type": "customer_message",
  "content": "I need help with my order",
  "channel": "telegram",
  "sentiment_score": 0.0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Next Steps

- [ ] Set up WhatsApp Cloud API (similar architecture)
- [ ] Create internal dashboard for viewing tickets
- [ ] Add human handoff functionality
- [ ] Implement message templates for structured responses
- [ ] Add analytics and reporting

## Security Notes

- Never commit your bot token to version control
- Use environment variables for sensitive data
- Consider implementing rate limiting
- Validate all incoming webhook data
- Use HTTPS for all webhook URLs
