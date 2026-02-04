"""
Escalated Tickets Inbox Component for Streamlit Dashboard
"""
import streamlit as st
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_TICKETS, COLLECTION_INTERACTIONS
from src.models import TicketStatus


def render_escalated_inbox(company_id: str):
    """
    Render escalated tickets inbox

    Args:
        company_id: Company ID from authenticated session (JWT)
    """
    st.header("📥 Tickets Escalados")

    tickets_col = get_collection(COLLECTION_TICKETS)
    interactions_col = get_collection(COLLECTION_INTERACTIONS)

    # Filters section
    st.markdown("### 🔍 Filtros")
    col_cat, col_tags = st.columns(2)

    with col_cat:
        category_filter = st.selectbox(
            "Categoria",
            ["Todas", "billing", "tech", "general"],
            index=0
        )

    with col_tags:
        # Get all unique tags for this company
        all_tags = tickets_col.distinct("tags", {"company_id": company_id})
        all_tags = [t for t in all_tags if t]  # Remove empty
        tag_filter = st.multiselect("Tags", all_tags, default=[])

    # Build query
    query = {
        "status": TicketStatus.ESCALATED,
        "company_id": company_id
    }
    if category_filter != "Todas":
        query["category"] = category_filter
    if tag_filter:
        query["tags"] = {"$in": tag_filter}

    # Fetch escalated tickets - CRITICAL: Filter by company_id for security
    escalated = list(tickets_col.find(query).sort("created_at", -1).limit(50))
    
    if not escalated:
        st.info("🎉 Nenhum ticket escalado no momento!")
        return
    
    col_metric, col_refresh = st.columns([3, 1])
    with col_metric:
        st.metric("Total Escalados", len(escalated))
    with col_refresh:
        if st.button("🔄 Atualizar", help="Atualizar conversas"):
            st.rerun()
    
    # Ticket selector
    ticket_options = {
        f"{t.get('ticket_id')} - {t.get('subject', 'Sem assunto')[:40]}": t.get('ticket_id')
        for t in escalated
    }
    
    selected_label = st.selectbox("Selecione um Ticket:", list(ticket_options.keys()))
    selected_ticket_id = ticket_options.get(selected_label)
    
    if selected_ticket_id:
        ticket = next((t for t in escalated if t.get("ticket_id") == selected_ticket_id), None)
        
        if ticket:
            st.markdown("---")

            # Ticket Info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**Prioridade:** {ticket.get('priority', 'P3')}")
            with col2:
                st.write(f"**Canal:** {ticket.get('channel', 'N/A')}")
            with col3:
                category = ticket.get('category', 'N/A')
                cat_emoji = "💰" if category == "billing" else "🔧" if category == "tech" else "📋"
                st.write(f"**Categoria:** {cat_emoji} {category}")
            with col4:
                created = ticket.get('created_at')
                if created:
                    st.write(f"**Criado:** {created.strftime('%d/%m %H:%M') if isinstance(created, datetime) else str(created)[:16]}")

            st.write(f"**Assunto:** {ticket.get('subject', 'N/A')}")
            st.write(f"**Descrição:** {ticket.get('description', 'N/A')}")

            # Display tags
            tags = ticket.get('tags', [])
            if tags:
                st.write("**Tags:** " + " ".join([f"`{tag}`" for tag in tags]))
            
            # AI Decision Insights Section
            st.markdown("### 🧠 AI Decision Insights")
            
            # Find the last interaction with AI metadata
            last_ai_interaction = interactions_col.find_one(
                {
                    "ticket_id": selected_ticket_id,
                    "ai_metadata": {"$exists": True, "$ne": None}
                },
                sort=[("created_at", -1)]
            )
            
            if last_ai_interaction and last_ai_interaction.get("ai_metadata"):
                ai_meta = last_ai_interaction["ai_metadata"]
                
                # Confidence Score with color indicator
                confidence = ai_meta.get("confidence_score", 0)
                if confidence >= 0.7:
                    conf_color = "🟢"
                    conf_status = "Alta"
                elif confidence >= 0.4:
                    conf_color = "🟡"
                    conf_status = "Média"
                else:
                    conf_color = "🔴"
                    conf_status = "Baixa"
                
                col_conf, col_type = st.columns(2)
                with col_conf:
                    st.metric("Confidence Score", f"{conf_color} {confidence:.0%} ({conf_status})")
                with col_type:
                    decision_type = ai_meta.get("decision_type", "N/A")
                    type_emoji = "⚠️" if decision_type == "escalation" else "✅" if decision_type == "resolution" else "📋"
                    st.write(f"**Tipo de Decisão:** {type_emoji} {decision_type.title() if decision_type else 'N/A'}")
                
                # Reasoning in expander
                reasoning = ai_meta.get("reasoning")
                if reasoning:
                    with st.expander("📝 AI Reasoning (clique para expandir)"):
                        st.write(reasoning)
                
                # Factors considered
                factors = ai_meta.get("factors", [])
                if factors:
                    st.write("**Fatores Considerados:**")
                    for factor in factors:
                        st.write(f"  • {factor}")
            else:
                st.info("ℹ️ Nenhuma metadata de AI disponível para este ticket.")
            
            st.markdown("---")
            
            # Interactions
            st.markdown("### 💬 Histórico de Conversas")
            interactions = list(interactions_col.find(
                {"ticket_id": selected_ticket_id}
            ).sort("created_at", 1))
            
            for i in interactions:
                i_type = i.get("type", "unknown")
                i_content = i.get("content", "")
                i_source = i.get("source", "")
                
                if i_type == "customer_message":
                    st.chat_message("user").write(i_content)
                else:
                    label = "🤖 Bot" if i_source != "human" else "👤 Humano"
                    st.chat_message("assistant").write(f"{label}: {i_content}")
            
            # Reply Form
            st.markdown("### ✍️ Responder")
            reply_text = st.text_area("Sua resposta:", key="reply_input")
            
            col_send, col_close = st.columns(2)
            with col_send:
                if st.button("📤 Enviar Resposta", type="primary"):
                    if reply_text:
                        _send_reply(selected_ticket_id, reply_text, close=False, company_id=company_id)
                        st.success("Resposta enviada!")
                        st.rerun()
                    else:
                        st.warning("Digite uma resposta.")

            with col_close:
                if st.button("✅ Resolver e Fechar"):
                    if reply_text:
                        _send_reply(selected_ticket_id, reply_text, close=True, company_id=company_id)
                        st.success("Ticket resolvido!")
                        st.rerun()
                    else:
                        st.warning("Digite uma resposta final antes de fechar.")


def _send_reply(ticket_id: str, reply_text: str, close: bool, company_id: str = None):
    """Send human reply and optionally close the ticket. Also sends to Telegram.

    Args:
        ticket_id: The ticket ID to reply to
        reply_text: The reply text
        close: Whether to close the ticket
        company_id: Company ID for security isolation (prevents IDOR)
    """
    import requests
    from src.config import settings

    tickets_col = get_collection(COLLECTION_TICKETS)
    interactions_col = get_collection(COLLECTION_INTERACTIONS)

    # Get ticket to find external_user_id (with company_id filter to prevent IDOR)
    query = {"ticket_id": ticket_id}
    if company_id:
        query["company_id"] = company_id
    ticket = tickets_col.find_one(query)
    
    # Add interaction
    interactions_col.insert_one({
        "ticket_id": ticket_id,
        "type": "agent_response",
        "content": reply_text,
        "source": "human",
        "created_at": datetime.utcnow()
    })
    
    # Update ticket
    update_data = {"updated_at": datetime.utcnow()}
    if close:
        update_data["status"] = TicketStatus.RESOLVED
        update_data["resolved_at"] = datetime.utcnow()
    
    tickets_col.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )
    
    # Send message to Telegram if applicable
    if ticket:
        external_user_id = ticket.get("external_user_id", "")
        channel = ticket.get("channel", "")
        
        # Check if it's a Telegram user
        if channel == "telegram" and external_user_id.startswith("telegram:"):
            try:
                chat_id = int(external_user_id.replace("telegram:", ""))
                bot_token = settings.telegram_bot_token
                
                if bot_token:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": f"👤 Atendente: {reply_text}",
                        "parse_mode": "HTML"
                    }
                    response = requests.post(url, json=payload, timeout=10)
                    if not response.ok:
                        st.error(f"Erro ao enviar para Telegram: {response.text}")
            except Exception as e:
                st.error(f"Erro ao enviar mensagem: {e}")
