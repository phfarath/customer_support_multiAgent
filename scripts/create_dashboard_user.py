"""
Script to create dashboard users

Usage:
    python scripts/create_dashboard_user.py \
        --email admin@techcorp.com \
        --password secure123 \
        --company-id techcorp_001 \
        --full-name "Admin User" \
        --role admin
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
from src.database import get_collection, COLLECTION_USERS
from src.models.user import User
import secrets


async def create_user(email: str, password: str, company_id: str, full_name: str, role: str):
    """
    Create dashboard user

    Args:
        email: User email
        password: Plain text password (will be hashed)
        company_id: Company ID
        full_name: Full name
        role: User role (operator or admin)
    """
    collection = get_collection(COLLECTION_USERS)

    # Check if user exists
    existing = await collection.find_one({"email": email})
    if existing:
        print(f"❌ User with email {email} already exists")
        print(f"   User ID: {existing.get('user_id')}")
        print(f"   Company: {existing.get('company_id')}")
        return

    # Create user
    user = User(
        user_id=f"user_{secrets.token_hex(8)}",
        email=email,
        password_hash=User.hash_password(password),
        company_id=company_id,
        full_name=full_name,
        role=role,
        active=True
    )

    await collection.insert_one(user.dict())

    print(f"\n✅ User created successfully!")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"User ID:     {user.user_id}")
    print(f"Email:       {user.email}")
    print(f"Full Name:   {user.full_name}")
    print(f"Company ID:  {user.company_id}")
    print(f"Role:        {user.role}")
    print(f"Active:      {user.active}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\n🔐 Login Information:")
    print(f"   Email:    {user.email}")
    print(f"   Password: {password}")
    print(f"\n🌐 Dashboard URL:")
    print(f"   http://localhost:8501")
    print(f"\n⚠️  IMPORTANT: Save these credentials securely.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create dashboard user for MultiAgent Customer Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create admin user
  python scripts/create_dashboard_user.py \\
      --email admin@techcorp.com \\
      --password Admin123! \\
      --company-id techcorp_001 \\
      --full-name "Admin Techcorp" \\
      --role admin

  # Create operator user
  python scripts/create_dashboard_user.py \\
      --email operator@techcorp.com \\
      --password Operator123! \\
      --company-id techcorp_001 \\
      --full-name "Operator Name"
        """
    )
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password (plain text)")
    parser.add_argument("--company-id", required=True, help="Company ID")
    parser.add_argument("--full-name", required=True, help="User's full name")
    parser.add_argument(
        "--role",
        default="operator",
        choices=["operator", "admin"],
        help="User role (default: operator)"
    )
    args = parser.parse_args()

    asyncio.run(create_user(
        email=args.email,
        password=args.password,
        company_id=args.company_id,
        full_name=args.full_name,
        role=args.role
    ))
