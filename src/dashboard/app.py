import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from src.dashboard.connection import get_collection, COLLECTION_COMPANY_CONFIGS

# Page Config
st.set_page_config(
    page_title="Admin Dashboard - MultiAgent Support",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    st.title("🤖 MultiAgent Customer Support Admin")
    
    # Initialize Session State
    if 'selected_company_id' not in st.session_state:
        st.session_state.selected_company_id = None
        
    if 'company_config' not in st.session_state:
        st.session_state.company_config = None

    # Sidebar Navigation
    with st.sidebar:
        st.header("Navegação")
        page = st.radio("Ir para:", ["Home/Login", "Configurações do Bot", "Produtos", "Logs"])
        
        st.markdown("---")
        if st.session_state.selected_company_id:
            st.success(f"Empresa: {st.session_state.company_config.get('company_name', 'Unknown')}")
            if st.button("Sair"):
                st.session_state.selected_company_id = None
                st.session_state.company_config = None
                st.rerun()
        else:
            st.warning("Nenhuma empresa selecionada")

    # Routing
    if page == "Home/Login":
        render_home()
    elif page == "Configurações do Bot":
        if check_auth():
            # Import dynamically to avoid circular imports or heavy loads on startup
            from src.dashboard.components.bot_config import render_bot_config
            render_bot_config()
    elif page == "Produtos":
        if check_auth():
            from src.dashboard.components.products_config import render_products_config
            render_products_config()
    elif page == "Logs":
        if check_auth():
            st.info("Em breve: Visualizador de Logs")

def check_auth():
    if not st.session_state.selected_company_id:
        st.error("Por favor, selecione uma empresa na página Home primeiro.")
        return False
    return True

def render_home():
    st.header("Seleção de Empresa")
    
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    
    # Simple form to "Login"
    company_id_input = st.text_input("Digite o ID da Empresa (ex: techcorp_001)", value="techcorp_001")
    
    if st.button("Acessar Painel"):
        if company_id_input:
            company = collection.find_one({"company_id": company_id_input})
            if company:
                st.session_state.selected_company_id = company.get("company_id")
                st.session_state.company_config = company
                st.success(f"Logado com sucesso na empresa: {company.get('company_name')}")
                st.rerun()
            else:
                st.error("Empresa não encontrada!")
        else:
            st.warning("Digite um ID válido.")

    st.markdown("---")
    st.subheader("Empresas Disponíveis")
    # List available companies for easier testing
    companies = list(collection.find({}, {"company_id": 1, "company_name": 1, "_id": 0}))
    if companies:
        for c in companies:
            st.markdown(f"- **{c.get('company_name')}** (`{c.get('company_id')}`)")
    else:
        st.info("Nenhuma empresa cadastrada ainda.")

if __name__ == "__main__":
    main()
