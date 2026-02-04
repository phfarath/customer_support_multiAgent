#!/usr/bin/env python3
"""
Setup Validation Script

Validates that all required components are properly configured:
- Environment variables
- MongoDB connection
- OpenAI API
- Telegram bot token
- Required collections and indexes

Usage:
    python scripts/validate_setup.py
    python scripts/validate_setup.py --fix  # Attempt to fix issues
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Tuple, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_check(name: str, passed: bool, message: str = ""):
    """Print a check result"""
    if passed:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}"
    else:
        status = f"{Colors.RED}❌ FAIL{Colors.END}"

    print(f"  {status}  {name}")
    if message:
        print(f"         {Colors.YELLOW}{message}{Colors.END}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"  {Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str):
    """Print an info message"""
    print(f"  {Colors.BLUE}ℹ️  {message}{Colors.END}")


class SetupValidator:
    """Validates the setup of the customer support system"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.fixes_available: List[str] = []

    def check_env_file(self) -> bool:
        """Check if .env file exists"""
        env_path = Path(__file__).parent.parent / ".env"
        env_example_path = Path(__file__).parent.parent / ".env.example"

        if env_path.exists():
            print_check(".env file exists", True)
            return True
        else:
            print_check(".env file exists", False,
                       f"Copy from .env.example: cp {env_example_path} {env_path}")
            self.fixes_available.append("cp .env.example .env")
            return False

    def check_required_env_vars(self) -> Tuple[bool, List[str]]:
        """Check required environment variables"""
        required_vars = {
            "MONGODB_URI": "MongoDB connection string",
            "DATABASE_NAME": "Database name",
            "OPENAI_API_KEY": "OpenAI API key for AI agents",
            "TELEGRAM_BOT_TOKEN": "Telegram bot token from @BotFather",
            "JWT_SECRET_KEY": "JWT secret for dashboard authentication",
        }

        optional_vars = {
            "SMTP_HOST": "Email server for escalations",
            "SMTP_USERNAME": "Email username",
            "SMTP_PASSWORD": "Email password",
            "TELEGRAM_WEBHOOK_SECRET": "Webhook security (required in production)",
        }

        missing = []
        placeholder_values = []

        # Load .env file
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)

        print("\n  Required Variables:")
        for var, description in required_vars.items():
            value = os.getenv(var, "")

            if not value:
                print_check(f"{var}", False, f"Missing: {description}")
                missing.append(var)
            elif value in ["your_openai_api_key_here", "your_telegram_bot_token_here",
                          "CHANGE_THIS_IN_PRODUCTION_TO_A_LONG_RANDOM_STRING",
                          "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"]:
                print_check(f"{var}", False, "Still has placeholder value")
                placeholder_values.append(var)
            else:
                # Mask sensitive values
                masked = value[:4] + "****" + value[-4:] if len(value) > 12 else "****"
                print_check(f"{var}", True, f"Set: {masked}")

        print("\n  Optional Variables:")
        for var, description in optional_vars.items():
            value = os.getenv(var, "")
            if value and value not in ["your_gmail_address@gmail.com", "your_gmail_app_password"]:
                print_check(f"{var}", True, "Configured")
            else:
                print_warning(f"{var}: Not configured ({description})")

        all_ok = len(missing) == 0 and len(placeholder_values) == 0
        return all_ok, missing + placeholder_values

    async def check_mongodb_connection(self) -> bool:
        """Check MongoDB connection"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from src.config import settings

            client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)

            # Test connection
            await client.admin.command('ping')

            # Get database info
            db = client[settings.database_name]
            collections = await db.list_collection_names()

            print_check("MongoDB connection", True, f"Connected to {settings.database_name}")
            print_info(f"Collections found: {len(collections)}")

            if collections:
                for col in collections[:5]:
                    count = await db[col].count_documents({})
                    print_info(f"  - {col}: {count} documents")
                if len(collections) > 5:
                    print_info(f"  ... and {len(collections) - 5} more")

            client.close()
            return True

        except Exception as e:
            print_check("MongoDB connection", False, str(e))
            self.errors.append(f"MongoDB: {str(e)}")
            return False

    async def check_openai_connection(self) -> bool:
        """Check OpenAI API connection"""
        try:
            from openai import OpenAI
            from src.config import settings

            client = OpenAI(api_key=settings.openai_api_key)

            # Test with a simple completion
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
                max_tokens=10
            )

            result = response.choices[0].message.content
            print_check("OpenAI API", True, f"Model: {settings.openai_model}, Response: {result}")
            return True

        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower():
                print_check("OpenAI API", False, "Invalid API key")
            elif "insufficient_quota" in error_msg.lower():
                print_check("OpenAI API", False, "Insufficient quota/credits")
            else:
                print_check("OpenAI API", False, error_msg[:100])
            self.errors.append(f"OpenAI: {error_msg}")
            return False

    async def check_telegram_bot(self) -> bool:
        """Check Telegram bot token"""
        try:
            import httpx
            from src.config import settings

            if not settings.telegram_bot_token:
                print_check("Telegram Bot", False, "Token not configured")
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe",
                    timeout=10.0
                )
                data = response.json()

                if data.get("ok"):
                    bot_info = data.get("result", {})
                    username = bot_info.get("username", "unknown")
                    print_check("Telegram Bot", True, f"@{username}")

                    # Check webhook
                    webhook_response = await client.get(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/getWebhookInfo",
                        timeout=10.0
                    )
                    webhook_data = webhook_response.json()

                    if webhook_data.get("ok"):
                        webhook_url = webhook_data.get("result", {}).get("url", "")
                        if webhook_url:
                            print_info(f"Webhook configured: {webhook_url}")
                        else:
                            print_warning("Webhook not configured (bot won't receive messages)")

                    return True
                else:
                    print_check("Telegram Bot", False, data.get("description", "Unknown error"))
                    return False

        except Exception as e:
            print_check("Telegram Bot", False, str(e))
            self.errors.append(f"Telegram: {str(e)}")
            return False

    async def check_required_collections(self) -> bool:
        """Check if required MongoDB collections exist"""
        required_collections = [
            "tickets",
            "interactions",
            "customers",
            "api_keys",
            "company_configs",
            "dashboard_users",
            "audit_logs",
        ]

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from src.config import settings

            client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            db = client[settings.database_name]

            existing = await db.list_collection_names()

            all_exist = True
            for col in required_collections:
                if col in existing:
                    print_check(f"Collection: {col}", True)
                else:
                    print_check(f"Collection: {col}", False, "Will be created on first use")
                    all_exist = False

            client.close()
            return all_exist

        except Exception as e:
            print_check("Collections check", False, str(e))
            return False

    async def check_api_keys(self) -> bool:
        """Check if any API keys exist"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from src.config import settings

            client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            db = client[settings.database_name]

            count = await db.api_keys.count_documents({"active": True})

            if count > 0:
                print_check("API Keys", True, f"{count} active key(s) found")
                return True
            else:
                print_check("API Keys", False, "No API keys found")
                print_info("Create one with: python scripts/create_initial_api_key.py --company-id YOUR_COMPANY --name 'Dev Key'")
                return False

        except Exception as e:
            print_check("API Keys check", False, str(e))
            return False

    async def check_company_config(self) -> bool:
        """Check if any company config exists"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from src.config import settings

            client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            db = client[settings.database_name]

            count = await db.company_configs.count_documents({})

            if count > 0:
                print_check("Company Config", True, f"{count} company config(s) found")

                # Show company IDs
                async for company in db.company_configs.find({}, {"company_id": 1, "company_name": 1}).limit(3):
                    print_info(f"  - {company.get('company_id')}: {company.get('company_name', 'N/A')}")

                return True
            else:
                print_check("Company Config", False, "No company configured")
                print_info("See GETTING_STARTED.md section 6.1 to create a company")
                return False

        except Exception as e:
            print_check("Company Config check", False, str(e))
            return False

    async def run_all_checks(self) -> bool:
        """Run all validation checks"""
        results = []

        # Environment checks
        print_header("Environment Configuration")
        results.append(self.check_env_file())
        env_ok, missing_vars = self.check_required_env_vars()
        results.append(env_ok)

        if not env_ok:
            print(f"\n{Colors.RED}Cannot continue without required environment variables.{Colors.END}")
            print(f"Please configure: {', '.join(missing_vars)}")
            return False

        # Service connectivity checks
        print_header("Service Connectivity")
        results.append(await self.check_mongodb_connection())
        results.append(await self.check_openai_connection())
        results.append(await self.check_telegram_bot())

        # Data checks
        print_header("Data Configuration")
        results.append(await self.check_required_collections())
        results.append(await self.check_api_keys())
        results.append(await self.check_company_config())

        # Summary
        print_header("Summary")

        passed = sum(results)
        total = len(results)

        if passed == total:
            print(f"{Colors.GREEN}{Colors.BOLD}All checks passed! ({passed}/{total}){Colors.END}")
            print(f"\n{Colors.GREEN}✨ Your system is ready to use!{Colors.END}")
            print(f"\nNext steps:")
            print(f"  1. Test the API: curl http://localhost:8000/api/health")
            print(f"  2. Send a message to your Telegram bot")
            print(f"  3. Access the dashboard: http://localhost:8501")
            return True
        else:
            failed = total - passed
            print(f"{Colors.YELLOW}{Colors.BOLD}Checks completed: {passed}/{total} passed, {failed} failed{Colors.END}")

            if self.errors:
                print(f"\n{Colors.RED}Errors:{Colors.END}")
                for error in self.errors:
                    print(f"  - {error}")

            print(f"\n{Colors.YELLOW}Please fix the issues above and run this script again.{Colors.END}")
            print(f"See GETTING_STARTED.md for detailed setup instructions.")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Validate Customer Support System Setup")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues automatically")
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Customer Support MultiAgent - Setup Validator        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Working Directory: {Path.cwd()}")

    validator = SetupValidator()
    success = await validator.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
