"""
Ticket lifecycle automation for escalated tickets.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from pymongo import ReturnDocument

from src.adapters.telegram_adapter import TelegramAdapter
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_TICKET_LIFECYCLE_EVENTS,
    COLLECTION_COMPANY_CONFIGS,
)
from src.models import TicketStatus, TicketLifecycleConfig

logger = logging.getLogger(__name__)


EVENT_FOLLOWUP_1 = "followup_1"
EVENT_FOLLOWUP_2 = "followup_2"
EVENT_AUTO_CLOSE = "auto_close"

EVENT_STATUS_PENDING = "pending"
EVENT_STATUS_EXECUTED = "executed"
EVENT_STATUS_CANCELLED = "cancelled"


def _safe_lifecycle_config(company_config: Optional[Dict[str, Any]]) -> TicketLifecycleConfig:
    if not company_config:
        return TicketLifecycleConfig()
    try:
        return TicketLifecycleConfig(**(company_config.get("lifecycle_config") or {}))
    except Exception:
        logger.warning("Invalid lifecycle_config for company %s, using defaults", company_config.get("company_id"))
        return TicketLifecycleConfig()


def _extract_telegram_chat_id(ticket: Dict[str, Any]) -> Optional[int]:
    if ticket.get("channel") != "telegram":
        return None
    external_user_id = ticket.get("external_user_id", "")
    if not external_user_id.startswith("telegram:"):
        return None
    chat_id_str = external_user_id.split(":", 1)[1]
    try:
        return int(chat_id_str)
    except ValueError:
        return None


async def cancel_pending_events(ticket_id: str) -> None:
    lifecycle_collection = get_collection(COLLECTION_TICKET_LIFECYCLE_EVENTS)
    await lifecycle_collection.update_many(
        {"ticket_id": ticket_id, "status": EVENT_STATUS_PENDING},
        {"$set": {"status": EVENT_STATUS_CANCELLED, "cancelled_at": datetime.utcnow()}},
    )


async def schedule_lifecycle_events_for_escalated_ticket(
    ticket: Dict[str, Any],
    company_config: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> None:
    lifecycle_cfg = _safe_lifecycle_config(company_config)
    if not lifecycle_cfg.enable_auto_followup and not lifecycle_cfg.enable_auto_close:
        return

    now = now or datetime.utcnow()
    ticket_id = ticket["ticket_id"]
    lifecycle_collection = get_collection(COLLECTION_TICKET_LIFECYCLE_EVENTS)
    tickets_collection = get_collection(COLLECTION_TICKETS)

    await cancel_pending_events(ticket_id)

    events = []
    if lifecycle_cfg.enable_auto_followup:
        events.append(
            {
                "ticket_id": ticket_id,
                "company_id": ticket.get("company_id"),
                "event_type": EVENT_FOLLOWUP_1,
                "scheduled_at": now + timedelta(hours=lifecycle_cfg.followup_1_hours),
                "status": EVENT_STATUS_PENDING,
                "created_at": now,
            }
        )
        events.append(
            {
                "ticket_id": ticket_id,
                "company_id": ticket.get("company_id"),
                "event_type": EVENT_FOLLOWUP_2,
                "scheduled_at": now + timedelta(hours=lifecycle_cfg.followup_2_hours),
                "status": EVENT_STATUS_PENDING,
                "created_at": now,
            }
        )
    if lifecycle_cfg.enable_auto_close:
        events.append(
            {
                "ticket_id": ticket_id,
                "company_id": ticket.get("company_id"),
                "event_type": EVENT_AUTO_CLOSE,
                "scheduled_at": now + timedelta(hours=lifecycle_cfg.auto_close_hours),
                "status": EVENT_STATUS_PENDING,
                "created_at": now,
            }
        )

    if events:
        await lifecycle_collection.insert_many(events)

    await tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$set": {
                "lifecycle_stage": "scheduled",
                "last_escalated_at": now,
            }
        },
    )


async def process_due_lifecycle_events(limit: int = 100) -> None:
    lifecycle_collection = get_collection(COLLECTION_TICKET_LIFECYCLE_EVENTS)
    tickets_collection = get_collection(COLLECTION_TICKETS)
    company_collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    adapter = TelegramAdapter()

    while True:
        now = datetime.utcnow()
        event = await lifecycle_collection.find_one_and_update(
            {
                "status": EVENT_STATUS_PENDING,
                "scheduled_at": {"$lte": now},
            },
            {"$set": {"status": EVENT_STATUS_EXECUTED, "executed_at": now}},
            sort=[("scheduled_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

        if not event:
            break
        if limit <= 0:
            break
        limit -= 1

        ticket = await tickets_collection.find_one({"ticket_id": event["ticket_id"]})
        if not ticket:
            continue

        company_config = await company_collection.find_one({"company_id": ticket.get("company_id")})
        lifecycle_cfg = _safe_lifecycle_config(company_config)

        # Ignore events for tickets no longer under escalation lifecycle.
        if ticket.get("status") != TicketStatus.ESCALATED:
            continue

        chat_id = _extract_telegram_chat_id(ticket)
        message = None
        stage = None

        if event["event_type"] == EVENT_FOLLOWUP_1 and lifecycle_cfg.enable_auto_followup:
            message = lifecycle_cfg.followup_1_message
            stage = "followup_1_sent"
        elif event["event_type"] == EVENT_FOLLOWUP_2 and lifecycle_cfg.enable_auto_followup:
            message = lifecycle_cfg.followup_2_message
            stage = "followup_2_sent"
        elif event["event_type"] == EVENT_AUTO_CLOSE and lifecycle_cfg.enable_auto_close:
            await tickets_collection.update_one(
                {"ticket_id": ticket["ticket_id"]},
                {
                    "$set": {
                        "status": TicketStatus.AUTO_RESOLVED,
                        "lifecycle_stage": "auto_closed",
                        "auto_closed_at": now,
                        "updated_at": now,
                    }
                },
            )
            message = lifecycle_cfg.auto_close_message
            stage = "auto_closed"

        if stage:
            await tickets_collection.update_one(
                {"ticket_id": ticket["ticket_id"]},
                {"$set": {"lifecycle_stage": stage, "updated_at": now}},
            )

        if message and chat_id:
            try:
                await adapter.send_message(chat_id, message)
            except Exception as exc:
                logger.error("Failed to send lifecycle message for ticket %s: %s", ticket["ticket_id"], exc)
