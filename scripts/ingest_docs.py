"""
Script to ingest documents into the Knowledge Base
"""
import sys
import os
import asyncio
import glob

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.rag.knowledge_base import knowledge_base
# Optional: import PDF loader if needed, but for now we'll do simple text/md
# from langchain_community.document_loaders import PyPDFLoader

async def ingest_file(file_path: str, company_id: str):
    print(f"📄 Processing: {file_path}")
    
    filename = os.path.basename(file_path)
    extension = os.path.splitext(filename)[1].lower()
    
    content = ""
    
    try:
        if extension in ['.txt', '.md', '.markdown']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
        elif extension == '.pdf':
            # Basic PDF text extraction
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            content = "\n".join([p.page_content for p in pages])
            
        else:
            print(f"⚠️ Skipping unsupported file type: {extension}")
            return

        if content:
            chunks = await knowledge_base.add_document(
                content=content,
                company_id=company_id,
                source=filename,
                doc_type="manual"
            )
            print(f"✅ Ingested {chunks} chunks for {filename}")
        else:
            print(f"⚠️ Warning: No content extracted from {filename}")
            
    except Exception as e:
        print(f"❌ Error ingesting {filename}: {e}")

async def run_ingestion(company_id: str = "techcorp_001"):
    print(f"🚀 Starting ingestion for Company: {company_id}")
    
    docs_dir = os.path.join(os.getcwd(), "docs", "knowledge_base")
    
    if not os.path.exists(docs_dir):
        print(f"❌ Directory not found: {docs_dir}")
        return

    # Find all supported files
    files = []
    for ext in ['*.txt', '*.md', '*.pdf']:
        files.extend(glob.glob(os.path.join(docs_dir, ext)))
    
    if not files:
        print("⚠️ No documents found to ingest.")
        return
        
    for file_path in files:
        await ingest_file(file_path, company_id)

    print("✨ Ingestion complete!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    if len(sys.argv) > 1:
        c_id = sys.argv[1]
    else:
        c_id = "techcorp_001"
        
    asyncio.run(run_ingestion(c_id))
