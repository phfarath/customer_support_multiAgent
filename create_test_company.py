"""
Script para criar uma empresa de teste no banco de dados
"""
import asyncio
from datetime import datetime
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.models.company_config import CompanyConfig, Team, KnowledgeBaseConfig

async def create_test_company():
    # Definição dos times
    sales_team = Team(
        team_id="sales",
        name="Vendas",
        description="Responsável por dúvidas sobre preços, planos, orçamentos e informações comerciais.",
        responsibilities=["pricing", "plans", "quotes", "product_info"],
        instructions="Seja persuasivo e focado em fechar negócios. Use a lista de produtos para informar preços.",
        is_sales=True
    )

    tech_team = Team(
        team_id="tech_support",
        name="Suporte Técnico",
        description="Responsável por problemas técnicos, bugs, configurações e erros no sistema.",
        responsibilities=["bug_report", "configuration", "access_issues", "outages"],
        instructions="Seja técnico e preciso. Peça detalhes do erro e logs se necessário.",
        is_sales=False
    )
    
    general_team = Team(
        team_id="general",
        name="Atendimento Geral",
        description="Dúvidas gerais, administrativas ou assuntos que não se encaixam em Vendas ou Suporte.",
        responsibilities=["general_inquiries", "account_status", "feedback"],
        instructions="Seja cordial e encaminhe para o setor correto se identificar necessidade específica.",
        is_sales=False
    )

    # Dados da empresa fictícia
    company_data = {
        "company_id": "techcorp_001",
        "company_name": "TechSolutions Integradora",
        "support_email": "suporte@techsolutions.com.br",
        "support_phone": "+5511999999999",
        "business_hours": {
            "mon-fri": "09:00-18:00",
            "sat": "09:00-13:00"
        },
        "bot_name": "TechBot",
        "bot_welcome_message": """
👋 Olá! Bem-vindo à TechSolutions. 

Sou o TechBot. Posso te ajudar com Vendas, Suporte Técnico ou Dúvidas Gerais.

Como posso ser útil hoje?
""",
        "bot_outside_hours_message": """
🌙 Olá! No momento estamos fora do nosso horário de atendimento (Seg-Sex 9h-18h).

Você pode deixar sua mensagem e nossa equipe responderá assim que retomarmos as atividades!
""",
        "products": [
            {"name": "Cloud Server Pro", "id": "prod_001", "price": "R$ 150,00/mês", "details": "Servidor VPS 4vCPU, 8GB RAM"},
            {"name": "Consultoria DevOps", "id": "serv_002", "price": "Sob consulta", "details": "Consultoria especializada para CI/CD e Kubernetes"}
        ],
        
        # Novos campos
        "teams": [sales_team, tech_team, general_team],
        "knowledge_base": KnowledgeBaseConfig(
            enabled=True,
            vector_db_collection="techcorp_knowledge"
        ),
        "escalation_contact": "-100123456789", # Exemplo de ID de grupo
        
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        # Validar com o modelo Pydantic
        company = CompanyConfig(**company_data)
        
        # Inserir no banco
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)
        
        # Usar update_one com upsert para evitar erro se já existir
        result = await collection.update_one(
            {"company_id": company.company_id},
            {"$set": company.model_dump(by_alias=True)},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"✅ Empresa de teste criada com sucesso! ID: {result.upserted_id}")
        else:
            print(f"✅ Empresa de teste atualizada com sucesso!")
            
        print(f"🆔 Company ID: {company.company_id}")
        print(f"🏢 Nome: {company.company_name}")
        print(f"👥 Times configurados: {[t.name for t in company.teams]}")
        
    except Exception as e:
        print(f"❌ Erro ao criar empresa: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Importar aqui para garantir que variáveis de ambiente carreguem se necessário
    from dotenv import load_dotenv
    load_dotenv()
    
    # Executar loop
    asyncio.run(create_test_company())
