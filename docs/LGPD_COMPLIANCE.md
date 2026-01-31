# LGPD Compliance Documentation

> **Última atualização:** 2026-01-31
> **Versão:** 1.0

---

## Visão Geral

Este documento descreve como o Customer Support MultiAgent está em conformidade com a Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018) e o Regulamento Geral sobre a Proteção de Dados (GDPR - EU 2016/679).

---

## 1. Princípios de Proteção de Dados

### 1.1 Minimização de Dados
- Coletamos apenas dados necessários para o atendimento
- PII é redatado antes do armazenamento
- Dados sensíveis nunca são expostos em logs

### 1.2 Limitação de Finalidade
- Dados são usados exclusivamente para suporte ao cliente
- Não compartilhamos dados com terceiros
- Analytics utiliza apenas dados agregados e anonimizados

### 1.3 Exatidão
- Clientes podem solicitar correção de dados
- Sistema de audit trail para rastreabilidade
- Versionamento de alterações

---

## 2. Dados Pessoais Tratados

### 2.1 Categorias de Dados

| Categoria | Exemplos | Tratamento |
|-----------|----------|------------|
| Identificação | Nome, email, telefone | Armazenado com criptografia |
| Financeiro | CPF, cartão de crédito | **SEMPRE REDATADO** |
| Comunicação | Mensagens de suporte | Armazenado com PII redatado |
| Técnico | IP, user agent | Logado temporariamente |

### 2.2 Dados Sensíveis (Art. 11 LGPD)
- **Não coletamos** dados sobre origem racial, convicções religiosas, opinião política, saúde, etc.
- Sistema detecta e redacta automaticamente dados financeiros

---

## 3. PII Detection & Redaction

### 3.1 Tipos de PII Detectados

| Tipo | Regex Pattern | Redação |
|------|---------------|---------|
| CPF | `\d{3}[\.]?\d{3}[\.]?\d{3}[-]?\d{2}` | `[CPF REDACTED]` |
| RG | `\d{1,2}[\.]?\d{3}[\.]?\d{3}[-]?[\dXx]` | `[RG REDACTED]` |
| Cartão de Crédito | Luhn-validated 16 dígitos | `[CREDIT CARD REDACTED]` |
| Email | RFC 5322 format | `[EMAIL REDACTED]` |
| Telefone | `\(?\d{2}\)?[-\s]?\d{4,5}[-\s]?\d{4}` | `[PHONE REDACTED]` |
| CEP | `\d{5}[-]?\d{3}` | `[CEP REDACTED]` |

### 3.2 Fluxo de Redação

```
┌─────────────────┐
│ Mensagem Cliente│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PII Detection   │ ◄── Regex + Validação
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PII Redaction   │ ◄── Substituição por placeholders
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Armazenamento   │ ◄── Apenas texto redatado
└─────────────────┘
```

### 3.3 Validação de Dados

- **CPF**: Validado com algoritmo de dígitos verificadores
- **Cartão de Crédito**: Validado com algoritmo de Luhn
- **Email**: Validado com formato RFC 5322

---

## 4. Direitos dos Titulares (Art. 18 LGPD)

### 4.1 Direito de Acesso
- Endpoint: `GET /api/customers/{customer_id}/data`
- Retorna todos os dados do cliente
- Requer autenticação do cliente

### 4.2 Direito de Retificação
- Endpoint: `PATCH /api/customers/{customer_id}`
- Permite atualização de dados incorretos
- Audit trail de todas as alterações

### 4.3 Direito de Eliminação (Art. 18, VI)
- Endpoint: `DELETE /api/customers/{customer_id}`
- Remove dados pessoais do sistema
- Mantém registros anonimizados para compliance

### 4.4 Portabilidade de Dados
- Endpoint: `GET /api/customers/{customer_id}/export`
- Exporta dados em formato JSON/CSV
- Inclui todas as interações do cliente

---

## 5. Segurança de Dados (Art. 46 LGPD)

### 5.1 Medidas Técnicas

| Medida | Implementação |
|--------|---------------|
| Criptografia em trânsito | TLS 1.3 obrigatório |
| Criptografia em repouso | MongoDB encryption at rest |
| Controle de acesso | RBAC + API Keys |
| Auditoria | Audit logs completos |
| Backup | Backup diário criptografado |

### 5.2 Medidas Organizacionais
- Treinamento de equipe sobre LGPD
- Políticas de acesso mínimo necessário
- Revisão periódica de permissões

---

## 6. Retenção de Dados

### 6.1 Períodos de Retenção

| Tipo de Dado | Período | Base Legal |
|--------------|---------|------------|
| Tickets de suporte | 5 anos | Art. 16, I LGPD |
| Logs de auditoria | 5 anos | Compliance |
| Dados de sessão | 30 dias | Necessidade técnica |
| Logs de acesso | 6 meses | Segurança |

### 6.2 Exclusão Automática
- Job diário para exclusão de dados expirados
- Notificação antes da exclusão
- Confirmação de exclusão no audit log

---

## 7. Incidentes de Segurança (Art. 48 LGPD)

### 7.1 Procedimento de Resposta

1. **Detecção**: Monitoramento contínuo de anomalias
2. **Contenção**: Isolamento imediato de sistemas afetados
3. **Avaliação**: Análise de impacto e dados afetados
4. **Notificação**: ANPD e titulares em 72 horas
5. **Remediação**: Correção e prevenção de recorrência

### 7.2 Contato para Incidentes
- Email: privacy@empresa.com
- Telefone: +55 (11) 9999-0000

---

## 8. Encarregado de Dados (DPO)

**Responsável**: [Nome do DPO]
**Email**: dpo@empresa.com
**Telefone**: +55 (11) 9999-0000

---

## 9. Base Legal para Tratamento (Art. 7 LGPD)

| Atividade | Base Legal |
|-----------|------------|
| Atendimento ao cliente | Execução de contrato |
| Melhoria do serviço | Legítimo interesse |
| Cumprimento legal | Obrigação legal |
| Analytics agregado | Legítimo interesse |

---

## 10. Transferência Internacional (Art. 33 LGPD)

### 10.1 Processamento de IA
- OpenAI API (EUA): Contrato com cláusulas padrão
- Dados enviados são **sempre redatados** de PII
- Nenhum dado pessoal é armazenado pela OpenAI

### 10.2 Infraestrutura
- Servidores principais: AWS São Paulo (sa-east-1)
- Backups: AWS São Paulo (sa-east-1)
- CDN: CloudFront com edge locations Brasil

---

## 11. Cookies e Rastreamento

- Dashboard não utiliza cookies de terceiros
- Apenas cookies de sessão necessários
- Sem tracking analytics invasivo

---

## 12. Referências

- [Lei 13.709/2018 (LGPD)](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [GDPR (EU 2016/679)](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [SECURITY.md](./SECURITY.md) - Documentação de segurança técnica
- [ANPD](https://www.gov.br/anpd/) - Autoridade Nacional de Proteção de Dados

---

## 13. Histórico de Revisões

| Versão | Data | Alterações |
|--------|------|------------|
| 1.0 | 2026-01-31 | Versão inicial com PII detection |

---

**Aprovado por**: [Nome do Responsável]
**Data de aprovação**: 2026-01-31
