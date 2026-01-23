import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_USERS, COLLECTION_COMPANY_CONFIGS
from src.models.user import User
from src.utils.jwt_handler import create_jwt_token, verify_jwt_token

# Page Config
st.set_page_config(
    page_title="Admin Dashboard - MultiAgent Support",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def verify_authentication():
    """
    Check if user is authenticated, redirect to login if not

    Returns:
        bool: True if authenticated, False otherwise
    """
    if 'jwt_token' not in st.session_state or not st.session_state.jwt_token:
        return False

    # Verify JWT
    payload = verify_jwt_token(st.session_state.jwt_token)
    if not payload:
        # Token invalid/expired
        st.session_state.jwt_token = None
        st.session_state.user_data = None
        return False

    # Store user data in session
    st.session_state.user_data = payload
    return True


def render_login():
    """Render login page"""
    st.title("🔐 Customer Support Dashboard - Login")

    st.markdown("""
    ### Bem-vindo ao Dashboard de Atendimento
    Faça login para acessar os tickets escalados e configurações do bot.
    """)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu@email.com")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("❌ Por favor, preencha email e senha")
                return

            # Authenticate
            users_col = get_collection(COLLECTION_USERS)
            user = users_col.find_one({"email": email})

            if not user:
                st.error("❌ Email ou senha incorretos")
                return

            # Verify password
            if not User.verify_password(password, user["password_hash"]):
                st.error("❌ Email ou senha incorretos")
                return

            # Check if active
            if not user.get("active", True):
                st.error("❌ Usuário desativado. Contate o administrador.")
                return

            # Create JWT token with all user data
            token = create_jwt_token(
                user_id=user["user_id"],
                company_id=user["company_id"],
                email=user["email"],
                full_name=user.get("full_name", email),
                role=user.get("role", "operator")
            )

            # Store in session
            st.session_state.jwt_token = token
            st.session_state.user_data = {
                "user_id": user["user_id"],
                "company_id": user["company_id"],
                "email": user["email"],
                "full_name": user.get("full_name", email),
                "role": user.get("role", "operator")
            }

            # Update last login
            users_col.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"last_login_at": datetime.now()}}
            )

            st.success(f"✅ Login bem-sucedido! Bem-vindo, {user.get('full_name', email)}")
            st.rerun()

    st.markdown("---")
    st.info("""
    **Nota:** Para criar um novo usuário, use o script:
    ```bash
    python scripts/create_dashboard_user.py \\
        --email seu@email.com \\
        --password SuaSenha123! \\
        --company-id sua_empresa \\
        --full-name "Seu Nome"
    ```
    """)


def render_sidebar():
    """Render sidebar with user info and logout"""
    st.sidebar.title("🤖 Dashboard")

    # User info with safe defaults
    user_data = st.session_state.user_data
    full_name = user_data.get('full_name', user_data.get('email', 'User'))
    email = user_data.get('email', 'N/A')
    company_id = user_data.get('company_id', 'N/A')
    role = user_data.get('role', 'operator')

    st.sidebar.markdown(f"**👤 {full_name}**")
    st.sidebar.markdown(f"📧 {email}")
    st.sidebar.markdown(f"🏢 {company_id}")

    if role:
        role_emoji = "👑" if role == "admin" else "👔"
        st.sidebar.markdown(f"{role_emoji} {role.title()}")

    st.sidebar.markdown("---")

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.jwt_token = None
        st.session_state.user_data = None
        st.success("Logout realizado com sucesso!")
        st.rerun()


def main():
    """Main app logic"""
    # Initialize session state
    if 'jwt_token' not in st.session_state:
        st.session_state.jwt_token = None
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None

    # Check authentication
    if not verify_authentication():
        render_login()
        return

    # Render sidebar with user info
    render_sidebar()

    # Navigation
    st.sidebar.markdown("---")
    st.sidebar.header("Navegação")
    page = st.sidebar.radio(
        "Ir para:",
        ["📥 Tickets Escalados", "🤖 Configuração do Bot", "📦 Produtos", "📊 Logs"],
        label_visibility="collapsed"
    )

    # Get company_id from authenticated user (JWT)
    company_id = st.session_state.user_data["company_id"]

    # Render pages
    if page == "📥 Tickets Escalados":
        from src.dashboard.components.escalated_inbox import render_escalated_inbox
        render_escalated_inbox(company_id)
    elif page == "🤖 Configuração do Bot":
        from src.dashboard.components.bot_config import render_bot_config
        render_bot_config(company_id)
    elif page == "📦 Produtos":
        from src.dashboard.components.products_config import render_products_config
        render_products_config(company_id)
    elif page == "📊 Logs":
        st.info("Em breve: Visualizador de Logs")


if __name__ == "__main__":
    main()
