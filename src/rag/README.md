# RAG Module - Retrieval Augmented Generation

> **Localização:** `src/rag/`
> **Propósito:** Sistema de knowledge base usando ChromaDB para respostas contextualizadas

---

## 📖 Visão Geral

Este módulo implementa **RAG (Retrieval Augmented Generation)** - um sistema que permite aos agentes de IA buscarem informações relevantes em uma base de conhecimento antes de gerar respostas.

### Como Funciona RAG

```
1. Cliente: "Como funciona o plano premium?"
   ↓
2. RAG busca em ChromaDB: docs sobre "plano premium"
   ↓
3. Retorna top-3 documentos mais relevantes
   ↓
4. ResolverAgent usa docs no prompt para OpenAI
   ↓
5. Resposta baseada em conhecimento real da empresa
```

### Benefícios

✅ **Respostas precisas** - Baseadas em documentação real
✅ **Reduz alucinações** - IA não inventa informações
✅ **Multi-tenancy** - Cada empresa tem seu próprio knowledge base
✅ **Escalável** - Adicionar novos documentos sem re-treinar modelo
✅ **Rastreável** - Sabe quais docs foram usados na resposta

---

## 📁 Estrutura de Arquivos

```
src/rag/
└── knowledge_base.py        # ⭐ ChromaDB wrapper e search

chroma_db/                   # Vector database storage (local)
└── {company_id}/           # Isolamento por empresa

scripts/
└── ingest_knowledge.py     # Script para ingerir documentos

docs/knowledge_base/        # Documentos de exemplo
├── manual_tecnico_v1.md
└── manual_test.md
```

---

## 🏗️ Arquitetura

### KnowledgeBase Class

Wrapper singleton para ChromaDB que gerencia:
- Conexão com ChromaDB
- Criação de collections por empresa
- Embedding de documentos
- Busca semântica

```python
from src.rag.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Ingerir documento
await kb.add_documents(
    company_id="comp_123",
    documents=[
        {"content": "...", "metadata": {"source": "manual.pdf", "page": 1}}
    ]
)

# Buscar documentos relevantes
results = await kb.search(
    query="Como funciona o refund?",
    company_id="comp_123",
    n_results=3
)
```

### ChromaDB Integration

**Vector Database:** ChromaDB (local, file-based)
**Embedding Model:** OpenAI `text-embedding-3-small`
**Distance Metric:** Cosine similarity
**Storage:** `./chroma_db/{company_id}/`

### Collection Schema

Cada empresa tem uma collection separada:

```python
collection_name = f"kb_{company_id}"

# Documento no ChromaDB
{
    "id": "doc_123",
    "embedding": [0.123, 0.456, ...],  # 1536 dimensions
    "document": "Texto completo do documento...",
    "metadata": {
        "source": "manual_tecnico.pdf",
        "page": 5,
        "section": "Políticas de Refund",
        "company_id": "comp_123",
        "ingested_at": "2026-01-20T10:00:00"
    }
}
```

---

## 🔧 API da KnowledgeBase

### Métodos Principais

#### 1. `add_documents(company_id, documents)`

Adiciona documentos ao knowledge base.

**Parâmetros:**
```python
company_id: str              # ID da empresa
documents: List[Dict]        # Lista de documentos
```

**Formato de documento:**
```python
{
    "content": str,          # Texto do documento
    "metadata": {            # Metadados opcionais
        "source": str,       # Nome do arquivo
        "page": int,         # Número da página
        "section": str,      # Seção do documento
        "url": str,          # URL original (se aplicável)
        "author": str,       # Autor
        "created_at": str    # Data de criação
    }
}
```

**Exemplo:**
```python
kb = KnowledgeBase()

await kb.add_documents(
    company_id="comp_123",
    documents=[
        {
            "content": "Nossa política de reembolso permite cancelamento em até 7 dias...",
            "metadata": {
                "source": "politicas.pdf",
                "section": "Refund Policy",
                "page": 3
            }
        },
        {
            "content": "O plano premium inclui suporte 24/7 e recursos avançados...",
            "metadata": {
                "source": "manual_produtos.pdf",
                "section": "Plans",
                "page": 10
            }
        }
    ]
)
```

#### 2. `search(query, company_id, n_results)`

Busca documentos relevantes usando similaridade semântica.

**Parâmetros:**
```python
query: str              # Query de busca
company_id: str         # ID da empresa
n_results: int = 3      # Número de resultados (default: 3)
```

**Retorno:**
```python
List[Dict] = [
    {
        "content": str,      # Texto do documento
        "metadata": Dict,    # Metadados
        "distance": float    # Distance score (0.0 - 2.0, menor = mais similar)
    },
    ...
]
```

**Exemplo:**
```python
results = await kb.search(
    query="Como funciona o processo de refund?",
    company_id="comp_123",
    n_results=3
)

for result in results:
    print(f"Content: {result['content'][:100]}...")
    print(f"Source: {result['metadata']['source']}")
    print(f"Similarity: {1 - result['distance']/2:.2%}")
    print("---")

# Output:
# Content: Nossa política de reembolso permite cancelamento em até 7 dias...
# Source: politicas.pdf
# Similarity: 92%
# ---
```

#### 3. `get_or_create_collection(company_id)`

Obtém ou cria collection para uma empresa.

**Parâmetros:**
```python
company_id: str         # ID da empresa
```

**Retorno:**
```python
Collection              # ChromaDB collection object
```

**Uso interno** - Chamado automaticamente por `add_documents()` e `search()`.

#### 4. `delete_collection(company_id)`

Remove collection de uma empresa (útil para testes ou reset).

**Parâmetros:**
```python
company_id: str         # ID da empresa
```

**Exemplo:**
```python
await kb.delete_collection("comp_123")
```

#### 5. `list_documents(company_id, limit)`

Lista documentos no knowledge base de uma empresa.

**Parâmetros:**
```python
company_id: str         # ID da empresa
limit: int = 100        # Limite de documentos (default: 100)
```

**Retorno:**
```python
List[Dict] = [
    {
        "id": str,
        "content": str,
        "metadata": Dict
    },
    ...
]
```

**Exemplo:**
```python
docs = await kb.list_documents("comp_123", limit=10)
print(f"Total docs: {len(docs)}")
```

---

## 🔗 Integração com ResolverAgent

O `ResolverAgent` usa RAG para gerar respostas contextualizadas:

```python
# src/agents/resolver_agent.py

async def execute(self, ticket_id, context, session=None):
    customer_message = context["last_message"]

    # 1. Busca no knowledge base
    kb = KnowledgeBase()
    kb_results = await kb.search(
        query=customer_message,
        company_id=self.company_id,
        n_results=3
    )

    # 2. Monta contexto enriquecido
    enriched_context = {
        "customer_message": customer_message,
        "knowledge_base": [r["content"] for r in kb_results],
        "sources": [r["metadata"]["source"] for r in kb_results],
        "company_policies": context["company_config"]["policies"]
    }

    # 3. Gera prompt para OpenAI
    prompt = f"""
    Você é um assistente de suporte.

    KNOWLEDGE BASE:
    {enriched_context["knowledge_base"]}

    POLÍTICAS:
    {enriched_context["company_policies"]}

    PERGUNTA DO CLIENTE:
    {customer_message}

    Responda usando as informações do knowledge base.
    """

    # 4. Chama OpenAI
    response = await self.call_openai(prompt)

    return AgentResult(
        success=True,
        data={
            "response": response,
            "kb_used": len(kb_results) > 0,
            "sources": enriched_context["sources"]
        }
    )
```

---

## 📄 Ingestão de Documentos

### Script de Ingestão

**Localização:** `scripts/ingest_knowledge.py`

```bash
# Ingerir um arquivo
python scripts/ingest_knowledge.py \
    --company-id comp_123 \
    --file docs/knowledge_base/manual_tecnico.pdf

# Ingerir uma pasta
python scripts/ingest_knowledge.py \
    --company-id comp_123 \
    --directory docs/knowledge_base/

# Ver documentos existentes
python scripts/ingest_knowledge.py \
    --company-id comp_123 \
    --list
```

### Chunking de Documentos

Documentos grandes são divididos em chunks menores:

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # ~250 tokens
    chunk_overlap=200,    # Overlap para contexto
    separators=["\n\n", "\n", ". ", " ", ""]
)

chunks = splitter.split_text(document_text)

# Cada chunk vira um documento separado
for i, chunk in enumerate(chunks):
    documents.append({
        "content": chunk,
        "metadata": {
            "source": "manual.pdf",
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
    })
```

**Por que chunking?**
- Documentos grandes não cabem no context window do LLM
- Chunks menores = busca mais precisa
- Overlap previne perda de contexto entre chunks

### Formatos Suportados

O script de ingestão suporta:

| Formato | Extensão | Processamento |
|---------|----------|---------------|
| Markdown | `.md` | Direct text extraction |
| PDF | `.pdf` | PyPDF2 ou pdfplumber |
| Text | `.txt` | Direct read |
| JSON | `.json` | Parse e extract text fields |
| HTML | `.html` | BeautifulSoup para extract text |

---

## 🔍 Como Funciona a Busca Semântica

### 1. Embedding da Query

```python
query = "Como funciona o refund?"

# OpenAI gera embedding (vetor de 1536 dimensões)
query_embedding = openai.embeddings.create(
    model="text-embedding-3-small",
    input=query
)

# query_embedding = [0.123, -0.456, 0.789, ...]
```

### 2. Busca por Similaridade

ChromaDB compara o embedding da query com todos os embeddings de documentos:

```python
# Calcula cosine similarity entre query e cada documento
similarities = []
for doc in documents:
    similarity = cosine_similarity(query_embedding, doc.embedding)
    similarities.append((doc, similarity))

# Ordena por similaridade (maior = mais similar)
similarities.sort(key=lambda x: x[1], reverse=True)

# Retorna top-N
return similarities[:n_results]
```

### 3. Resultado

```python
[
    {
        "content": "Nossa política de reembolso...",
        "distance": 0.15,  # Menor = mais similar
        "metadata": {"source": "politicas.pdf"}
    },
    {
        "content": "Para solicitar refund...",
        "distance": 0.23,
        "metadata": {"source": "faq.md"}
    },
    {
        "content": "Reembolsos são processados em...",
        "distance": 0.31,
        "metadata": {"source": "manual.pdf"}
    }
]
```

---

## 🎯 Exemplos de Uso

### Exemplo 1: Adicionar Documentos via API

```python
from src.rag.knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Adicionar política de refund
await kb.add_documents(
    company_id="comp_abc",
    documents=[
        {
            "content": """
            POLÍTICA DE REEMBOLSO

            1. Cancelamento em até 7 dias: reembolso total
            2. Cancelamento entre 8-30 dias: reembolso de 50%
            3. Após 30 dias: sem reembolso

            Para solicitar, envie email para financeiro@empresa.com
            """,
            "metadata": {
                "source": "politica_refund.pdf",
                "section": "Refund Policy",
                "version": "v2.0"
            }
        }
    ]
)
```

### Exemplo 2: Buscar e Usar em Prompt

```python
# Cliente pergunta
query = "Quero cancelar meu plano e pedir reembolso"

# Busca no KB
results = await kb.search(query, company_id="comp_abc", n_results=2)

# Monta prompt
kb_context = "\n\n".join([r["content"] for r in results])

prompt = f"""
Baseado na política abaixo, responda ao cliente:

POLÍTICA:
{kb_context}

CLIENTE:
{query}

Seja claro sobre as condições.
"""

response = await openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
# Output: "Entendo que você deseja cancelar. Segundo nossa política,
#          se você cancelar em até 7 dias, receberá reembolso total..."
```

### Exemplo 3: Ingestão de Múltiplos Arquivos

```python
import os
from pathlib import Path

kb_dir = Path("docs/knowledge_base/")

for file in kb_dir.glob("*.md"):
    content = file.read_text()

    await kb.add_documents(
        company_id="comp_abc",
        documents=[
            {
                "content": content,
                "metadata": {
                    "source": file.name,
                    "path": str(file),
                    "ingested_at": datetime.now().isoformat()
                }
            }
        ]
    )

print(f"Ingeridos {len(list(kb_dir.glob('*.md')))} arquivos")
```

---

## 🧪 Testando RAG

### Teste de Busca

```python
import pytest
from src.rag.knowledge_base import KnowledgeBase

@pytest.mark.asyncio
async def test_search_returns_relevant_docs():
    kb = KnowledgeBase()

    # Setup: adiciona docs de teste
    await kb.add_documents(
        company_id="test_comp",
        documents=[
            {
                "content": "Política de reembolso: 7 dias para cancelar",
                "metadata": {"source": "test_policy.txt"}
            },
            {
                "content": "Nossos produtos incluem plano básico e premium",
                "metadata": {"source": "test_products.txt"}
            }
        ]
    )

    # Test: busca por "refund"
    results = await kb.search("quero reembolso", "test_comp", n_results=1)

    # Assert: deve retornar doc sobre reembolso
    assert len(results) == 1
    assert "reembolso" in results[0]["content"].lower()
    assert results[0]["metadata"]["source"] == "test_policy.txt"

    # Cleanup
    await kb.delete_collection("test_comp")
```

### Teste E2E com ResolverAgent

Ver: `tests/scenarios/test_rag.py`

---

## ⚙️ Configuração

### Environment Variables

```bash
# OpenAI (para embeddings)
OPENAI_API_KEY=sk-...

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db  # Local storage path
```

### ChromaDB Settings

```python
# src/rag/knowledge_base.py

import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db",
    anonymized_telemetry=False
))
```

---

## 🚀 Performance e Escalabilidade

### Benchmarks

| Operação | Tempo (avg) | Documentos |
|----------|-------------|------------|
| Embedding (1 doc) | ~200ms | 1 |
| Search (1 query) | ~50ms | 1000 docs |
| Add documents (batch) | ~2s | 100 docs |

### Otimizações

1. **Batch embedding:**
   ```python
   # Em vez de 1 por 1
   for doc in docs:
       embedding = embed(doc)

   # Batch (mais rápido)
   embeddings = embed_batch(docs)  # 10x faster
   ```

2. **Caching de embeddings:**
   ChromaDB persiste embeddings em disco, não precisa re-calcular.

3. **Index optimization:**
   ChromaDB usa HNSW (Hierarchical Navigable Small World) para busca rápida.

### Limites

| Métrica | Limite | Nota |
|---------|--------|------|
| Docs por collection | ~1M | Performance degrada após isso |
| Tamanho de doc | ~8K tokens | Dividir em chunks se maior |
| Dimensões embedding | 1536 | OpenAI text-embedding-3-small |
| Storage | ~500MB/100K docs | Depende do tamanho dos docs |

---

## 🔧 Manutenção

### Backup de Knowledge Base

```bash
# Backup do ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/

# Restore
tar -xzf chroma_backup_20260120.tar.gz
```

### Limpeza de Collections

```python
# Remover collection de empresa que não existe mais
kb = KnowledgeBase()
await kb.delete_collection("old_company_id")
```

### Re-index Documentos

```python
# Se mudar modelo de embedding, precisa re-indexar
kb = KnowledgeBase()

# 1. Backup docs
old_docs = await kb.list_documents("comp_123")

# 2. Delete collection
await kb.delete_collection("comp_123")

# 3. Re-add com novo embedding
await kb.add_documents("comp_123", old_docs)
```

---

## 🐛 Troubleshooting

### RAG não retorna resultados

**Problema:** `search()` retorna lista vazia

**Soluções:**
1. Verificar se documents foram ingeridos:
   ```python
   docs = await kb.list_documents("comp_123")
   print(f"Total docs: {len(docs)}")
   ```

2. Check ChromaDB directory:
   ```bash
   ls -la chroma_db/
   ```

3. Verify collection exists:
   ```python
   collection = kb.get_or_create_collection("comp_123")
   print(f"Doc count: {collection.count()}")
   ```

### Embeddings muito caros

**Problema:** Custo alto de OpenAI embeddings

**Soluções:**
1. Use modelo menor (mas menos preciso):
   ```python
   model = "text-embedding-ada-002"  # Mais barato
   ```

2. Cache embeddings (já implementado no ChromaDB)

3. Considere modelo local (sentence-transformers):
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')  # Grátis!
   ```

### ChromaDB corrompido

**Problema:** Erro ao iniciar ChromaDB

**Solução:**
```bash
# Delete e recrie
rm -rf chroma_db/
python scripts/ingest_knowledge.py --company-id comp_123 --directory docs/
```

---

## 📚 Referências

### Internal Docs
- **ARCHITECTURE.md** - Visão geral do projeto
- **src/agents/README.md** - Como ResolverAgent usa RAG
- **scripts/ingest_knowledge.py** - Script de ingestão

### External Docs
- ChromaDB: https://docs.trychroma.com/
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
- LangChain Text Splitters: https://python.langchain.com/docs/modules/data_connection/document_transformers/

---

## 🎓 Best Practices

### 1. Chunking Inteligente

```python
# ✅ BOM - Respeita fronteiras semânticas
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " "]  # Quebra em parágrafos primeiro
)

# ❌ RUIM - Quebra no meio da palavra
chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
```

### 2. Metadata Rico

```python
# ✅ BOM - Metadata útil para filtering
{
    "content": "...",
    "metadata": {
        "source": "manual_v2.pdf",
        "section": "Billing",
        "page": 10,
        "version": "2.0",
        "language": "pt-BR",
        "last_updated": "2026-01-20"
    }
}

# ❌ RUIM - Sem metadata
{
    "content": "..."
}
```

### 3. Validação de Resultados

```python
# ✅ BOM - Valida qualidade dos results
results = await kb.search(query, company_id, n_results=3)

# Filter por distance threshold
quality_results = [r for r in results if r["distance"] < 0.5]

if len(quality_results) == 0:
    # Nenhum resultado relevante, usar fallback
    response = "Não encontrei informações específicas sobre isso..."
else:
    # Usar results
    pass
```

---

**Última atualização:** 2026-01-20
**Versão:** 1.0
**Mantenedor:** Aethera Labs Team
