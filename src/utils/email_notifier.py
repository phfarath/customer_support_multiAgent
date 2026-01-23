"""
SMTP email notifier for escalation to human agents
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from src.config import settings
from src.utils.openai_client import get_openai_client


logger = logging.getLogger(__name__)


def _format_interactions(interactions: List[Dict[str, Any]]) -> str:
    lines = []
    for interaction in interactions:
        created_at = interaction.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        interaction_type = interaction.get("type", "unknown")
        content = interaction.get("content", "")
        lines.append(f"- [{created_at}] {interaction_type}: {content}")
    return "\n".join(lines) if lines else "- (no recent interactions found)"


async def _build_summary(
    ticket: Dict[str, Any],
    interactions: List[Dict[str, Any]],
    escalation_reasons: List[str]
) -> Dict[str, str]:
    subject = ticket.get("subject", "")
    description = ticket.get("description", "")
    priority = ticket.get("priority", "P3")
    channel = ticket.get("channel", "unknown")

    interaction_context = "\n".join(
        f"- {i.get('type')}: {i.get('content', '')}"
        for i in interactions[-6:]
    )

    system_prompt = (
        "You are a support assistant summarizing a customer escalation. "
        "Return JSON with keys: summary (1-2 sentences), main_issue (short phrase)."
    )
    user_message = (
        f"Ticket subject: {subject}\n"
        f"Description: {description}\n"
        f"Priority: {priority}\n"
        f"Channel: {channel}\n"
        f"Escalation reasons: {escalation_reasons}\n"
        f"Recent interactions:\n{interaction_context}\n"
    )

    try:
        client = get_openai_client()
        result = await client.json_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=200
        )
        summary = str(result.get("summary", "")).strip()
        main_issue = str(result.get("main_issue", "")).strip()
        if summary and main_issue:
            return {"summary": summary, "main_issue": main_issue}
    except Exception as e:
        logger.warning(f"Failed to generate escalation summary: {e}")

    return {
        "summary": "Summary unavailable (automatic summary failed).",
        "main_issue": "Unknown"
    }


def _send_email_sync(
    subject: str,
    body: str,
    to_email: str
) -> None:
    from_email = settings.smtp_from or settings.smtp_username
    if not from_email:
        raise ValueError("SMTP_FROM or SMTP_USERNAME must be set")

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


async def send_escalation_email(
    ticket: Dict[str, Any],
    interactions: List[Dict[str, Any]],
    escalation_reasons: List[str],
    company_name: Optional[str],
    to_email: Optional[str]
) -> bool:
    if not to_email:
        logger.warning("No escalation email configured; skipping notification")
        return False

    summary_data = await _build_summary(ticket, interactions, escalation_reasons)

    ticket_id = ticket.get("ticket_id", "unknown")
    company_label = company_name or ticket.get("company_id") or "Unknown Company"
    subject = f"[Escalation] {company_label} - {ticket_id}"

    body = "\n".join([
        f"Company: {company_label}",
        f"Ticket ID: {ticket_id}",
        f"Channel: {ticket.get('channel', 'unknown')}",
        f"Priority: {ticket.get('priority', 'P3')}",
        f"Status: {ticket.get('status', 'unknown')}",
        f"Customer: {ticket.get('external_user_id', ticket.get('customer_id', 'unknown'))}",
        "",
        f"Main issue: {summary_data['main_issue']}",
        f"Summary: {summary_data['summary']}",
        "",
        "Escalation reasons:",
        "\n".join([f"- {r}" for r in escalation_reasons]) or "- (none provided)",
        "",
        "Last 3 messages:",
        _format_interactions(interactions[-3:]),
        "",
        "Search in DB by ticket_id to view full context."
    ])

    try:
        await asyncio.to_thread(_send_email_sync, subject, body, to_email)
        logger.info(f"Escalation email sent to {to_email} for ticket {ticket_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send escalation email: {e}", exc_info=True)
        return False
