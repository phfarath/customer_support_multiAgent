"""
Setup script for configuring a new company in the MultiAgent system
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


async def setup_company():
    """
    Setup a new company configuration interactively
    
    This script will:
    1. Collect company information
    2. Create company config via API
    3. Test the configuration
    """
    print("=== Configuração de Empresa ===\n")
    
    # Collect company information
    company_id = input("ID da empresa (ex: empresa1, minhaempresa): ").strip()
    
    if not company_id:
        print("❌ ID da empresa é obrigatório!")
        return
    
    company_name = input("Nome da empresa: ").strip()
    
    print("\n--- Informações de Contato ---")
    support_email = input("Email de suporte (opcional): ").strip() or None
    support_phone = input("Telefone de suporte (opcional): ").strip() or None
    
    print("\n--- Políticas ---")
    refund_policy = input("Política de reembolso (opcional, pressione Enter para pular): ").strip() or None
    cancellation_policy = input("Política de cancelamento (opcional, pressione Enter para pular): ").strip() or None
    
    print("\n--- Métodos de Pagamento ---")
    payment_methods_input = input("Métodos de pagamento aceitos (separados por vírgula, opcional): ").strip()
    payment_methods = [pm.strip() for pm in payment_methods_input.split(",") if pm.strip()] if payment_methods_input else None
    
    print("\n--- Produtos/Serviços ---")
    print("Adicione produtos/serviços (um por linha, linha vazia para terminar):")
    products = []
    while True:
        product = input("  ").strip()
        if not product:
            break
        products.append({"name": product})
    
    print("\n--- Horário de Atendimento ---")
    print("Formato: dia=horas (ex: Seg-Sex:09:00-18:00)")
    business_hours_input = input("Horário de atendimento (opcional): ").strip() or None
    
    business_hours = None
    if business_hours_input:
        try:
            # Parse business hours format: day=hours
            parts = business_hours_input.split("=")
            if len(parts) == 2:
                business_hours = {parts[0].strip(): parts[1].strip()}
        except Exception as e:
            print(f"⚠️  Formato de horário inválido, ignorando: {e}")
    
    print("\n--- Configuração do Bot ---")
    bot_name = input("Nome do bot (opcional, ex: Suporte Bot): ").strip() or None
    welcome_message = input("Mensagem de boas-vindas (opcional): ").strip() or None
    
    print("\n--- Instruções Personalizadas ---")
    custom_instructions = input("Instruções personalizadas para o bot (opcional, pressione Enter para pular): ").strip() or None
    
    # Build company config
    config_data = {
        "company_id": company_id,
        "company_name": company_name,
        "support_email": support_email,
        "support_phone": support_phone,
        "refund_policy": refund_policy,
        "cancellation_policy": cancellation_policy,
        "payment_methods": payment_methods,
        "products": products,
        "business_hours": business_hours,
        "bot_name": bot_name,
        "bot_welcome_message": welcome_message
    }
    
    # Display summary
    print("\n=== Resumo da Configuração ===")
    print(f"ID da Empresa: {config_data['company_id']}")
    print(f"Nome: {config_data['company_name']}")
    print(f"Email de Suporte: {config_data['support_email'] or 'Não definido'}")
    print(f"Telefone de Suporte: {config_data['support_phone'] or 'Não definido'}")
    print(f"Política de Reembolso: {config_data['refund_policy'] or 'Não definida'}")
    print(f"Política de Cancelamento: {config_data['cancellation_policy'] or 'Não definida'}")
    print(f"Métodos de Pagamento: {', '.join([pm['name'] for pm in config_data['payment_methods']]) if config_data['payment_methods'] else 'Não definidos'}")
    print(f"Produtos/Serviços: {len(config_data['products'])} item(ns)")
    print(f"Horário de Atendimento: {config_data['business_hours'] or 'Não definido'}")
    print(f"Nome do Bot: {config_data['bot_name'] or 'Padrão'}")
    print(f"Mensagem de Boas-vindas: {config_data['bot_welcome_message'] or 'Padrão'}")
    print(f"Instruções Personalizadas: {config_data['custom_instructions'] or 'Nenhuma'}")
    
    # Confirm
    confirm = input("\n\nCriar configuração? (s/n): ").strip().lower()
    if confirm != 's':
        print("❌ Cancelado.")
        return
    
    # Create company config via API
    print("\n📡 Criando configuração da empresa...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/companies/",
                json=config_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Configuração criada com sucesso!")
                print(f"   ID da Configuração: {result.get('_id')}")
                print("\n📝 Próximos Passos:")
                print("1. Configure seu bot do Telegram para usar este company_id")
                print("   - Adicione company_id aos metadados do webhook")
                print(f"   - Ou use a API: POST /api/companies/{company_id}/webhook")
                print("\n   Para testar:")
                print(f"   curl -X POST 'http://localhost:8000/api/companies/{company_id}/webhook' \\")
                print(f"   -d '{{\"url\": \"https://seu-ngrok-url.com/telegram/webhook\"}}'")
            else:
                print(f"❌ Erro ao criar configuração: {response.status_code}")
                print(f"   Detalhes: {response.text}")
                
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            print("\nCertifique-se de que o servidor está rodando em http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(setup_company())
