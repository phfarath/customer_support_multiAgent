"""
Script to create initial API key for a company (bootstrap).

This script is used to create the first API key for a company,
solving the bootstrap problem where you need an API key to create API keys.

Usage:
    python scripts/create_initial_api_key.py --company-id techcorp_001 --name "Initial Key"
"""
import asyncio
import argparse
import sys
import os

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_collection, COLLECTION_API_KEYS
from src.models.api_key import APIKey


async def create_initial_key(company_id: str, name: str):
    """
    Create initial API key for bootstrap

    Args:
        company_id: Company identifier
        name: Description for the key
    """
    collection = get_collection(COLLECTION_API_KEYS)

    # Check if company already has keys
    existing_count = await collection.count_documents({"company_id": company_id})
    if existing_count > 0:
        print(f"\n⚠️  Warning: Company '{company_id}' already has {existing_count} API key(s).")
        proceed = input("Do you want to create another key? (y/n): ")
        if proceed.lower() != 'y':
            print("Aborted.")
            return

    # Create key
    api_key = APIKey(
        company_id=company_id,
        name=name,
        permissions=["read", "write", "admin"]
    )

    # Insert into database
    await collection.insert_one(api_key.dict())

    print(f"\n{'='*80}")
    print(f"✅ API Key created successfully!")
    print(f"{'='*80}")
    print(f"\n📋 Details:")
    print(f"  Company ID: {api_key.company_id}")
    print(f"  Key ID:     {api_key.key_id}")
    print(f"  Name:       {api_key.name}")
    print(f"  Created:    {api_key.created_at}")
    print(f"\n🔑 API Key:")
    print(f"  {api_key.api_key}")
    print(f"\n⚠️  IMPORTANT:")
    print(f"  - Save this API key securely. It won't be shown again.")
    print(f"  - Add it to your .env file as: API_KEY={api_key.api_key}")
    print(f"  - Use it in HTTP requests with header: X-API-Key: {api_key.api_key}")
    print(f"\n📝 Usage Example:")
    print(f'  curl -H "X-API-Key: {api_key.api_key}" http://localhost:8000/api/tickets')
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create initial API key for a company (bootstrap)"
    )
    parser.add_argument(
        "--company-id",
        required=True,
        help="Company identifier (e.g., techcorp_001)"
    )
    parser.add_argument(
        "--name",
        default="Initial API Key",
        help="Description/name for the key (default: 'Initial API Key')"
    )
    args = parser.parse_args()

    try:
        asyncio.run(create_initial_key(args.company_id, args.name))
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
    except Exception as e:
        print(f"\n❌ Error creating API key: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
