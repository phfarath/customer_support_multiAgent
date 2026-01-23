"""
Script to seed companies and trigger RAG ingestion for tests
"""
import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.models.company_config import CompanyConfig, Team, KnowledgeBaseConfig
from src.rag.knowledge_base import knowledge_base

# Sample Manual Content
MANUAL_CONTENT = """# Manual Técnico - TechSolutions Integradora (TESTE)

## 1. Configuração de DNS
Para apontar seu domínio para nossos servidores, utilize as seguintes entradas:
- **Tipo A**: `@` -> `192.168.10.55`
- **CNAME**: `www` -> `proxy.techsolutions.com.br`

## 2. Limites da API
O plano Standard permite até 1000 requisições por minuto.
Porta MySQL: 3306.
"""

async def seed_rag_documents(company_id: str):
    """Creates a temporary manual file and ingests it"""
    print(f"📚 Seeding RAG for {company_id}...")
    
    # Ensure dir exists
    docs_dir = os.path.join(os.getcwd(), "docs", "knowledge_base")
    os.makedirs(docs_dir, exist_ok=True)
    
    file_path = os.path.join(docs_dir, "manual_test.md")
    
    # Write file
    with open(file_path, "w") as f:
        f.write(MANUAL_CONTENT)
        
    # Ingest
    chunks = await knowledge_base.add_document(
        content=MANUAL_CONTENT,
        company_id=company_id,
        source="manual_test.md",
        doc_type="manual"
    )
    print(f"   ✅ Ingested {chunks} chunks.")


async def seed_companies():
    print("🏢 Seeding companies...")
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    
    # 1. TechCorp (Full Features: Sales, RAG)
    tech_config = CompanyConfig(
        company_id="techcorp_001",
        company_name="TechSolutions Tests",
        support_email="support@tech.test",
        teams=[
            Team(
                team_id="sales",
                name="Vendas",
                description="Equipe de Vendas",
                instructions="Foque em vender.",
                is_sales=True
            ),
            Team(
                team_id="tech",
                name="Suporte Técnico",
                description="Problemas técnicos",
                is_sales=False
            )
        ],
        knowledge_base=KnowledgeBaseConfig(enabled=True, vector_db_collection="tech_knowledge"),
        products=[
            {"name": "Produto Teste", "id": "p1", "price": "R$ 999,00", "details": "Produto de teste"}
        ],
        business_hours={"mon-fri": "09:00-18:00"}
    )
    
    # 2. RetailInc (Basic)
    retail_config = CompanyConfig(
        company_id="retail_001",
        company_name="Retail Inc Tests",
        teams=[
            Team(team_id="general", name="Atendimento", description="Geral", is_sales=False)
        ]
    )
    
    # Insert
    for config in [tech_config, retail_config]:
        await collection.update_one(
            {"company_id": config.company_id},
            {"$set": config.model_dump(by_alias=True)},
            upsert=True
        )
        print(f"   ✅ Seeded {config.company_id}")
        
    # Seed RAG for TechCorp
    await seed_rag_documents("techcorp_001")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(seed_companies())
