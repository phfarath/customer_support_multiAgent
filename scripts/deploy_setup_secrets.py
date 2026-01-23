#!/usr/bin/env python3
"""
AWS Secrets Manager Setup Script

Creates/updates secrets required for ECS deployment.

Usage:
    python scripts/deploy_setup_secrets.py --env production --region us-east-1

Secrets created:
    - customer-support/{env}/mongodb-uri
    - customer-support/{env}/openai-key
    - customer-support/{env}/jwt-secret
    - customer-support/{env}/telegram-token
    - customer-support/{env}/smtp-password
"""

import argparse
import json
import sys
import os
from typing import Dict, Any

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


class SecretsManager:
    """AWS Secrets Manager helper"""

    def __init__(self, region: str, environment: str):
        self.region = region
        self.environment = environment
        self.client = boto3.client("secretsmanager", region_name=region)
        self.prefix = f"customer-support/{environment}"

    def create_or_update_secret(self, name: str, value: str, description: str = ""):
        """Create or update a secret"""
        secret_name = f"{self.prefix}/{name}"

        try:
            # Try to update existing secret
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=value
            )
            print(f"✓ Updated secret: {secret_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create new secret
                self.client.create_secret(
                    Name=secret_name,
                    Description=description or f"{name} for {self.environment}",
                    SecretString=value,
                    Tags=[
                        {"Key": "Environment", "Value": self.environment},
                        {"Key": "Application", "Value": "customer-support-multiagent"},
                    ]
                )
                print(f"✓ Created secret: {secret_name}")
            else:
                raise

    def get_secret_arn(self, name: str) -> str:
        """Get ARN of a secret"""
        secret_name = f"{self.prefix}/{name}"
        try:
            response = self.client.describe_secret(SecretId=secret_name)
            return response["ARN"]
        except ClientError:
            return ""

    def setup_all_secrets(self, secrets_dict: Dict[str, str]):
        """Setup all required secrets"""
        print("=" * 60)
        print(f"Setting up AWS Secrets Manager - {self.environment}")
        print("=" * 60)

        for name, value in secrets_dict.items():
            if not value or value == "REQUIRED" or value.startswith("your_"):
                print(f"⚠ Skipping {name} - no value provided")
                continue

            self.create_or_update_secret(name, value)

        print("\n" + "=" * 60)
        print("✓ Secrets setup completed")
        print("=" * 60)

        # Print ARNs for reference
        print("\nSecret ARNs (for ECS task definition):")
        for name in secrets_dict.keys():
            arn = self.get_secret_arn(name)
            if arn:
                print(f"  {name}: {arn}")


def load_secrets_from_env() -> Dict[str, str]:
    """Load secrets from environment variables or .env file"""
    secrets = {}

    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Required secrets
    secret_mapping = {
        "mongodb-uri": "MONGODB_URI",
        "openai-key": "OPENAI_API_KEY",
        "jwt-secret": "JWT_SECRET_KEY",
        "telegram-token": "TELEGRAM_BOT_TOKEN",
        "smtp-password": "SMTP_PASSWORD",
    }

    for secret_name, env_var in secret_mapping.items():
        value = os.getenv(env_var, "")
        if value:
            secrets[secret_name] = value
        else:
            print(f"⚠ Warning: {env_var} not found in environment")
            secrets[secret_name] = "REQUIRED"

    return secrets


def prompt_for_secrets() -> Dict[str, str]:
    """Interactively prompt user for secrets"""
    print("\nEnter secret values (or press Enter to skip):")
    print("-" * 60)

    secrets = {}

    # MongoDB URI
    mongodb_uri = input("MongoDB URI (mongodb+srv://...): ").strip()
    if mongodb_uri:
        secrets["mongodb-uri"] = mongodb_uri

    # OpenAI API Key
    openai_key = input("OpenAI API Key (sk-...): ").strip()
    if openai_key:
        secrets["openai-key"] = openai_key

    # JWT Secret
    jwt_secret = input("JWT Secret Key (random 32+ chars): ").strip()
    if not jwt_secret:
        import secrets as sec
        jwt_secret = sec.token_urlsafe(32)
        print(f"  Generated: {jwt_secret}")
    secrets["jwt-secret"] = jwt_secret

    # Telegram Token
    telegram_token = input("Telegram Bot Token (123456:ABC-DEF...): ").strip()
    if telegram_token:
        secrets["telegram-token"] = telegram_token

    # SMTP Password
    smtp_password = input("SMTP Password (Gmail app password): ").strip()
    if smtp_password:
        secrets["smtp-password"] = smtp_password

    return secrets


def main():
    parser = argparse.ArgumentParser(
        description="Setup AWS Secrets Manager for ECS deployment"
    )
    parser.add_argument(
        "--env",
        "--environment",
        required=True,
        choices=["development", "staging", "production"],
        help="Deployment environment"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Load secrets from environment variables/.env file"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Prompt for secrets interactively"
    )

    args = parser.parse_args()

    # Validate AWS credentials
    try:
        boto3.client("sts").get_caller_identity()
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("Configure with: aws configure")
        sys.exit(1)

    # Get secrets
    if args.from_env:
        print("Loading secrets from environment variables...")
        secrets = load_secrets_from_env()
    elif args.interactive:
        secrets = prompt_for_secrets()
    else:
        print("ERROR: Specify --from-env or --interactive")
        print("Example: python scripts/deploy_setup_secrets.py --env production --interactive")
        sys.exit(1)

    if not secrets:
        print("ERROR: No secrets to create")
        sys.exit(1)

    # Create secrets manager and setup
    manager = SecretsManager(region=args.region, environment=args.env)
    manager.setup_all_secrets(secrets)

    print(f"\n✓ Secrets configured for environment: {args.env}")
    print(f"Region: {args.region}")
    print("\nNext step: Deploy to ECS")
    print(f"  python scripts/deploy_ecs.py --env {args.env} --region {args.region}")


if __name__ == "__main__":
    main()
