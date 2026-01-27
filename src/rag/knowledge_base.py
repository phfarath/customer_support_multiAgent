"""
Knowledge Base Module using ChromaDB and OpenAI Embeddings
"""
import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional

class KnowledgeBase:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeBase, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize ChromaDB client and embeddings"""
        from dotenv import load_dotenv
        load_dotenv()
        
        self.persist_directory = os.path.join(os.getcwd(), "chroma_db")
        
        # Initialize Chromium DB Client
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Initialize LangChain Embeddings (for use with splitters if needed, though Chroma handles it internally usually)
        # But here we will pass the embedding function to Chroma
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
             print("WARNING: OPENAI_API_KEY not found. Embeddings will fail.")
        
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        
        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def get_collection(self, collection_name: str = "company_knowledge"):
        """Get or create a ChromaDB collection"""
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.openai_ef
        )

    async def add_document(
        self, 
        content: str, 
        company_id: str, 
        source: str,
        doc_type: str = "general",
        collection_name: str = "company_knowledge"
    ):
        """
        Chunk and add a document to the vector store
        """
        collection = self.get_collection(collection_name)
        
        # Split content
        chunks = self.text_splitter.split_text(content)
        
        if not chunks:
            return 0
            
        ids = [f"{company_id}_{source}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "company_id": company_id,
                "source": source,
                "doc_type": doc_type,
                "chunk_index": i
            } for i in range(len(chunks))
        ]
        
        # Add to Chroma
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(chunks)

    async def search(
        self, 
        query: str, 
        company_id: str, 
        k: int = 3,
        collection_name: str = "company_knowledge"
    ) -> List[str]:
        """
        Search for relevant context in the vector store
        """
        collection = self.get_collection(collection_name)
        
        results = collection.query(
            query_texts=[query],
            n_results=k,
            where={"company_id": company_id}
        )
        
        if results and results['documents']:
            return results['documents'][0]
        
        return []

    async def add_ticket_summary(
        self,
        summary: str,
        ticket_id: str,
        customer_id: str,
        company_id: str,
        collection_name: str = "customer_summaries"
    ) -> bool:
        """
        Index a ticket summary for cross-ticket context retrieval.
        
        Args:
            summary: The AI-generated conversation summary
            ticket_id: The resolved ticket ID
            customer_id: The customer identifier
            company_id: The company identifier
            collection_name: ChromaDB collection for summaries
            
        Returns:
            True if successfully indexed
        """
        collection = self.get_collection(collection_name)
        
        doc_id = f"{company_id}_{customer_id}_{ticket_id}"
        metadata = {
            "company_id": company_id,
            "customer_id": customer_id,
            "ticket_id": ticket_id,
            "doc_type": "ticket_summary"
        }
        
        try:
            collection.add(
                documents=[summary],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            print(f"Failed to index ticket summary: {e}")
            return False

    async def search_customer_context(
        self,
        query: str,
        customer_id: str,
        company_id: str,
        k: int = 3,
        collection_name: str = "customer_summaries"
    ) -> List[str]:
        """
        Search for relevant past ticket summaries for a specific customer.
        
        Args:
            query: The search query (current ticket description/message)
            customer_id: The customer to search history for
            company_id: The company identifier
            k: Number of results to return
            collection_name: ChromaDB collection for summaries
            
        Returns:
            List of relevant past ticket summaries
        """
        collection = self.get_collection(collection_name)
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=k,
                where={
                    "$and": [
                        {"company_id": company_id},
                        {"customer_id": customer_id}
                    ]
                }
            )
            
            if results and results['documents']:
                return results['documents'][0]
        except Exception as e:
            print(f"Customer context search failed: {e}")
        
        return []

# Singleton instance
knowledge_base = KnowledgeBase()
