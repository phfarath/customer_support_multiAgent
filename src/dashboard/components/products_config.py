"""
Products Configuration Component for Streamlit Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_COMPANY_CONFIGS


def render_products_config(company_id: str):
    """
    Render products configuration editor

    Args:
        company_id: Company ID from authenticated session (JWT)
    """
    st.header("📦 Produtos e Serviços")

    # Load company config from database
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    config = collection.find_one({"company_id": company_id})

    if not config:
        st.error(f"❌ Configuração não encontrada para empresa: {company_id}")
        st.info("Por favor, crie uma configuração usando a API ou o script de configuração.")
        return

    products = config.get("products", [])

    st.info("📝 Edite os produtos abaixo. O bot usará essas informações para responder sobre o que a empresa vende.")

    # Convert list of dicts to DataFrame for easier editing
    if products:
        df = pd.DataFrame(products)
    else:
        df = pd.DataFrame(columns=["name", "id", "description"])

    # Ensure columns exist
    for col in ["name", "id", "description"]:
        if col not in df.columns:
            df[col] = ""

    # Editor
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Nome do Produto", required=True),
            "id": st.column_config.TextColumn("ID (Opcional)"),
            "description": st.column_config.TextColumn("Descrição Curta", width="large"),
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Salvar Produtos", use_container_width=True):
        try:
            # Convert back to list of dicts
            # Filter out empty rows
            new_products = []
            for _, row in edited_df.iterrows():
                if row["name"]:  # Only save if name exists
                    new_products.append({
                        "name": row["name"],
                        "id": row["id"],
                        "description": row["description"]
                    })

            # Update configuration - SECURITY: company_id filter ensures isolation
            result = collection.update_one(
                {"company_id": company_id},  # ← CRITICAL: Ensures only own config is updated
                {"$set": {
                    "products": new_products,
                    "updated_at": datetime.utcnow()
                }}
            )

            if result.modified_count > 0:
                st.success(f"✅ Lista de produtos salva! ({len(new_products)} itens)")
                st.rerun()
            else:
                st.warning("Nenhuma alteração detectada.")

        except Exception as e:
            st.error(f"❌ Erro ao salvar: {str(e)}")

    # Display current products count
    if products:
        st.markdown("---")
        st.metric("Total de Produtos Cadastrados", len(products))
