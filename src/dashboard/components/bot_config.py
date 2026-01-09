import streamlit as st
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_COMPANY_CONFIGS

def render_bot_config():
    st.header("Configurações do Bot")
    
    if not st.session_state.company_config:
        st.error("Erro interno: config não carregada")
        return

    config = st.session_state.company_config
    
    with st.form("bot_config_form"):
        st.subheader("Identidade")
        bot_name = st.text_input("Nome do Bot", value=config.get("bot_name", ""))
        
        st.subheader("Mensagens")
        welcome_msg = st.text_area("Mensagem de Boas-vindas", value=config.get("bot_welcome_message", ""), height=150, help="Mensagem enviada no primeiro contato.")
        
        outside_hours_msg = st.text_area("Mensagem Fora do Horário", value=config.get("bot_outside_hours_message", ""), height=100, help="Mensagem enviada quando a empresa está fechada.")
        
        submitted = st.form_submit_button("Salvar Alterações")
        
        if submitted:
            try:
                collection = get_collection(COLLECTION_COMPANY_CONFIGS)
                collection.update_one(
                    {"company_id": config["company_id"]},
                    {"$set": {
                        "bot_name": bot_name,
                        "bot_welcome_message": welcome_msg,
                        "bot_outside_hours_message": outside_hours_msg,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                # Update session state
                st.session_state.company_config["bot_name"] = bot_name
                st.session_state.company_config["bot_welcome_message"] = welcome_msg
                st.session_state.company_config["bot_outside_hours_message"] = outside_hours_msg
                
                st.success("Configurações salvas com sucesso! O bot já está atualizado.")
            except Exception as e:
                st.error(f"Erro ao salvar: {str(e)}")
