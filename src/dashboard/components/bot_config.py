"""
Bot Configuration Component for Streamlit Dashboard
"""
import streamlit as st
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_COMPANY_CONFIGS


def render_bot_config(company_id: str):
    """
    Render bot configuration form

    Args:
        company_id: Company ID from authenticated session (JWT)
    """
    st.header("🤖 Configurações do Bot")

    # Load company config from database
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    config = collection.find_one({"company_id": company_id})

    if not config:
        st.error(f"❌ Configuração não encontrada para empresa: {company_id}")
        st.info("Por favor, crie uma configuração usando a API ou o script de configuração.")
        return

    with st.form("bot_config_form"):
        st.subheader("Identidade")
        bot_name = st.text_input(
            "Nome do Bot",
            value=config.get("bot_name", ""),
            help="Nome que o bot usará nas conversas"
        )

        st.subheader("Mensagens")
        welcome_msg = st.text_area(
            "Mensagem de Boas-vindas",
            value=config.get("bot_welcome_message", ""),
            height=150,
            help="Mensagem enviada no primeiro contato."
        )

        outside_hours_msg = st.text_area(
            "Mensagem Fora do Horário",
            value=config.get("bot_outside_hours_message", ""),
            height=100,
            help="Mensagem enviada quando a empresa está fechada."
        )

        submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)

        if submitted:
            try:
                # Update configuration - SECURITY: company_id filter ensures isolation
                result = collection.update_one(
                    {"company_id": company_id},  # ← CRITICAL: Ensures only own config is updated
                    {"$set": {
                        "bot_name": bot_name,
                        "bot_welcome_message": welcome_msg,
                        "bot_outside_hours_message": outside_hours_msg,
                        "updated_at": datetime.utcnow()
                    }}
                )

                if result.modified_count > 0:
                    st.success("✅ Configurações salvas com sucesso! O bot já está atualizado.")
                    st.rerun()
                else:
                    st.warning("Nenhuma alteração detectada.")

            except Exception as e:
                st.error(f"❌ Erro ao salvar: {str(e)}")

    # Display current configuration summary
    st.markdown("---")
    st.subheader("📋 Resumo da Configuração")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nome do Bot", config.get("bot_name", "N/A"))
    with col2:
        st.metric("Empresa", config.get("company_name", company_id))
