import streamlit as st
import pandas as pd
from datetime import datetime
from src.dashboard.connection import get_collection, COLLECTION_COMPANY_CONFIGS

def render_products_config():
    st.header("Produtos e Serviços")
    
    if not st.session_state.company_config:
        return

    config = st.session_state.company_config
    products = config.get("products", [])
    
    st.info("Edite os produtos abaixo. O bot usará essas informações para responder sobre o que a empresa vende.")
    
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
    
    if st.button("Salvar Produtos"):
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
            
            collection = get_collection(COLLECTION_COMPANY_CONFIGS)
            collection.update_one(
                {"company_id": config["company_id"]},
                {"$set": {
                    "products": new_products,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Update session state
            st.session_state.company_config["products"] = new_products
            st.success(f"Lista de produtos salva! ({len(new_products)} itens)")
            
        except Exception as e:
            st.error(f"Erro ao salvar: {str(e)}")
