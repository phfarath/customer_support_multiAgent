# Manual Técnico - TechSolutions Integradora

## 1. Configuração de DNS
Para apontar seu domínio para nossos servidores, utilize as seguintes entradas:
- **Tipo A**: `@` -> `192.168.10.55`
- **CNAME**: `www` -> `proxy.techsolutions.com.br`

**Importante**: A propagação pode levar até 48 horas.

## 2. Configuração de Firewall
Nosso sistema bloqueia conexões externas por padrão. Para liberar acesso ao banco de dados:
1. Acesse o Painel de Controle > Segurança.
2. Adicione o IP de origem na Whitelist.
3. Porta padrão MySQL: `3306`.
4. Porta padrão PostgreSQL: `5432`.

## 3. Limites da API
O plano Standard permite até 1000 requisições por minuto.
O retorno HTTP 429 indica que você excedeu esse limite.
Para aumentar, contate o suporte para upgrade para o plano Enterprise.

## 4. Integração com Webhook
Para receber notificações de eventos, configure a URL de callback em:
`Configurações > Webhooks > Adicionar Endpoint`
O payload será enviado em JSON com a assinatura HMAC no header `X-Signature`.
