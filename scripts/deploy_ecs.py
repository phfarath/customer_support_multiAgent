#!/usr/bin/env python3
"""
AWS ECS Deployment Script for Customer Support MultiAgent System

This script automates the deployment of the application to AWS ECS:
- Creates/updates ECR repository
- Builds and pushes Docker image to ECR
- Creates/updates ECS task definition
- Updates ECS service
- Monitors deployment status

Usage:
    python scripts/deploy_ecs.py --env production --region us-east-1

Requirements:
    - AWS CLI configured with credentials
    - boto3 installed: pip install boto3
    - Docker running locally
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


class ECSDeployer:
    """AWS ECS deployment orchestrator"""

    def __init__(
        self,
        region: str,
        environment: str,
        cluster_name: Optional[str] = None,
        service_name: Optional[str] = None,
    ):
        self.region = region
        self.environment = environment
        self.cluster_name = cluster_name or f"customer-support-{environment}"
        self.service_name = service_name or f"customer-support-api-{environment}"
        self.repository_name = "customer-support-multiagent"

        # AWS clients
        self.ecr_client = boto3.client("ecr", region_name=region)
        self.ecs_client = boto3.client("ecs", region_name=region)
        self.ec2_client = boto3.client("ec2", region_name=region)
        self.logs_client = boto3.client("logs", region_name=region)

        # Get account ID
        sts_client = boto3.client("sts", region_name=region)
        self.account_id = sts_client.get_caller_identity()["Account"]

        # Image tag (using git commit hash + timestamp)
        self.image_tag = self._get_image_tag()
        self.ecr_image_uri = f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/{self.repository_name}:{self.image_tag}"

    def _get_image_tag(self) -> str:
        """Generate image tag from git commit hash and timestamp"""
        try:
            git_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.STDOUT
            ).decode().strip()
        except subprocess.CalledProcessError:
            git_hash = "unknown"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{self.environment}-{git_hash}-{timestamp}"

    def create_ecr_repository(self) -> str:
        """Create ECR repository if it doesn't exist"""
        print(f"\n[1/6] Checking ECR repository: {self.repository_name}")

        try:
            response = self.ecr_client.describe_repositories(
                repositoryNames=[self.repository_name]
            )
            repo_uri = response["repositories"][0]["repositoryUri"]
            print(f"✓ Repository already exists: {repo_uri}")
            return repo_uri
        except ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryNotFoundException":
                print(f"Creating ECR repository: {self.repository_name}")
                response = self.ecr_client.create_repository(
                    repositoryName=self.repository_name,
                    imageScanningConfiguration={"scanOnPush": True},
                    encryptionConfiguration={"encryptionType": "AES256"},
                    tags=[
                        {"Key": "Environment", "Value": self.environment},
                        {"Key": "Application", "Value": "customer-support-multiagent"},
                    ]
                )
                repo_uri = response["repository"]["repositoryUri"]
                print(f"✓ Repository created: {repo_uri}")
                return repo_uri
            else:
                raise

    def build_and_push_image(self):
        """Build Docker image and push to ECR"""
        print(f"\n[2/6] Building and pushing Docker image")
        print(f"Image tag: {self.image_tag}")

        # Get ECR login token
        print("Authenticating with ECR...")
        login_response = self.ecr_client.get_authorization_token()
        token = login_response["authorizationData"][0]["authorizationToken"]
        endpoint = login_response["authorizationData"][0]["proxyEndpoint"]

        # Docker login to ECR
        subprocess.run(
            f"aws ecr get-login-password --region {self.region} | "
            f"docker login --username AWS --password-stdin {endpoint}",
            shell=True,
            check=True
        )

        # Build image
        print(f"Building image: {self.ecr_image_uri}")
        subprocess.run(
            ["docker", "build", "-t", self.ecr_image_uri, "."],
            check=True
        )

        # Tag as latest for environment
        latest_tag = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{self.repository_name}:{self.environment}-latest"
        subprocess.run(
            ["docker", "tag", self.ecr_image_uri, latest_tag],
            check=True
        )

        # Push both tags
        print(f"Pushing image to ECR...")
        subprocess.run(["docker", "push", self.ecr_image_uri], check=True)
        subprocess.run(["docker", "push", latest_tag], check=True)

        print(f"✓ Image pushed: {self.ecr_image_uri}")

    def create_log_group(self):
        """Create CloudWatch log group for ECS"""
        log_group_name = f"/ecs/customer-support-{self.environment}"

        try:
            self.logs_client.create_log_group(logGroupName=log_group_name)
            print(f"✓ Created log group: {log_group_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                print(f"✓ Log group already exists: {log_group_name}")
            else:
                raise

    def register_task_definition(self, secrets: Dict[str, str]) -> str:
        """Register new ECS task definition"""
        print(f"\n[3/6] Registering ECS task definition")

        # Create log group first
        self.create_log_group()

        task_definition = {
            "family": f"customer-support-{self.environment}",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "1024",  # 1 vCPU
            "memory": "2048",  # 2 GB
            "executionRoleArn": f"arn:aws:iam::{self.account_id}:role/ecsTaskExecutionRole",
            "taskRoleArn": f"arn:aws:iam::{self.account_id}:role/ecsTaskRole",
            "containerDefinitions": [
                {
                    "name": "api",
                    "image": self.ecr_image_uri,
                    "essential": True,
                    "portMappings": [
                        {
                            "containerPort": 8000,
                            "protocol": "tcp"
                        }
                    ],
                    "environment": [
                        {"name": "API_HOST", "value": "0.0.0.0"},
                        {"name": "API_PORT", "value": "8000"},
                        {"name": "API_RELOAD", "value": "False"},
                        {"name": "LOG_LEVEL", "value": "INFO"},
                        {"name": "ENVIRONMENT", "value": self.environment},
                    ],
                    "secrets": [
                        {
                            "name": "MONGODB_URI",
                            "valueFrom": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:customer-support/{self.environment}/mongodb-uri"
                        },
                        {
                            "name": "OPENAI_API_KEY",
                            "valueFrom": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:customer-support/{self.environment}/openai-key"
                        },
                        {
                            "name": "JWT_SECRET_KEY",
                            "valueFrom": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:customer-support/{self.environment}/jwt-secret"
                        },
                        {
                            "name": "TELEGRAM_BOT_TOKEN",
                            "valueFrom": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:customer-support/{self.environment}/telegram-token"
                        },
                        {
                            "name": "SMTP_PASSWORD",
                            "valueFrom": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:customer-support/{self.environment}/smtp-password"
                        },
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/ecs/customer-support-{self.environment}",
                            "awslogs-region": self.region,
                            "awslogs-stream-prefix": "api"
                        }
                    },
                    "healthCheck": {
                        "command": [
                            "CMD-SHELL",
                            "curl -f http://localhost:8000/api/health || exit 1"
                        ],
                        "interval": 30,
                        "timeout": 5,
                        "retries": 3,
                        "startPeriod": 60
                    }
                }
            ],
            "tags": [
                {"key": "Environment", "value": self.environment},
                {"key": "Application", "value": "customer-support-multiagent"},
                {"key": "ImageTag", "value": self.image_tag},
            ]
        }

        response = self.ecs_client.register_task_definition(**task_definition)
        task_def_arn = response["taskDefinition"]["taskDefinitionArn"]

        print(f"✓ Task definition registered: {task_def_arn}")
        return task_def_arn

    def update_service(self, task_definition_arn: str):
        """Update ECS service with new task definition"""
        print(f"\n[4/6] Updating ECS service: {self.service_name}")

        try:
            response = self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                taskDefinition=task_definition_arn,
                forceNewDeployment=True,
                deploymentConfiguration={
                    "maximumPercent": 200,
                    "minimumHealthyPercent": 100
                }
            )
            print(f"✓ Service update initiated")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ServiceNotFoundException":
                print(f"⚠ Service not found. Please create the service first.")
                print(f"Use AWS Console or CLI to create service: {self.service_name}")
                return False
            else:
                raise

    def wait_for_deployment(self, timeout: int = 600):
        """Wait for ECS deployment to complete"""
        print(f"\n[5/6] Monitoring deployment (timeout: {timeout}s)")

        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                print("⚠ Deployment timeout reached")
                return False

            response = self.ecs_client.describe_services(
                cluster=self.cluster_name,
                services=[self.service_name]
            )

            if not response["services"]:
                print("⚠ Service not found")
                return False

            service = response["services"][0]
            deployments = service["deployments"]

            # Check if only one deployment (new one)
            if len(deployments) == 1 and deployments[0]["status"] == "PRIMARY":
                running_count = deployments[0]["runningCount"]
                desired_count = deployments[0]["desiredCount"]

                if running_count == desired_count:
                    print(f"✓ Deployment completed successfully!")
                    print(f"  Running tasks: {running_count}/{desired_count}")
                    return True

            # Print status
            print(f"  Deployments: {len(deployments)}, Status: {deployments[0]['status']}, "
                  f"Running: {deployments[0]['runningCount']}/{deployments[0]['desiredCount']}")

            time.sleep(10)

    def get_service_info(self):
        """Get and display service information"""
        print(f"\n[6/6] Service Information")

        try:
            response = self.ecs_client.describe_services(
                cluster=self.cluster_name,
                services=[self.service_name]
            )

            if not response["services"]:
                print("⚠ Service not found")
                return

            service = response["services"][0]

            print(f"\nService: {service['serviceName']}")
            print(f"Status: {service['status']}")
            print(f"Running tasks: {service['runningCount']}/{service['desiredCount']}")
            print(f"Task definition: {service['taskDefinition']}")

            # Get load balancer info if exists
            if service.get("loadBalancers"):
                lb = service["loadBalancers"][0]
                print(f"\nLoad Balancer:")
                print(f"  Target Group: {lb.get('targetGroupArn', 'N/A')}")

            print(f"\nLogs: https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#logsV2:log-groups/log-group/$252Fecs$252Fcustomer-support-{self.environment}")

        except ClientError as e:
            print(f"Error getting service info: {e}")

    def deploy(self):
        """Execute full deployment pipeline"""
        print("=" * 60)
        print(f"AWS ECS Deployment - Environment: {self.environment}")
        print(f"Region: {self.region}")
        print(f"Cluster: {self.cluster_name}")
        print(f"Service: {self.service_name}")
        print("=" * 60)

        try:
            # Step 1: Create ECR repository
            self.create_ecr_repository()

            # Step 2: Build and push image
            self.build_and_push_image()

            # Step 3: Register task definition
            task_def_arn = self.register_task_definition(secrets={})

            # Step 4: Update service
            updated = self.update_service(task_def_arn)

            if not updated:
                print("\n⚠ Deployment stopped - service needs to be created first")
                return False

            # Step 5: Wait for deployment
            success = self.wait_for_deployment()

            # Step 6: Show service info
            self.get_service_info()

            if success:
                print("\n" + "=" * 60)
                print("✓ DEPLOYMENT SUCCESSFUL")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("⚠ DEPLOYMENT INCOMPLETE")
                print("=" * 60)

            return success

        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Customer Support MultiAgent to AWS ECS"
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
        "--cluster",
        help="ECS cluster name (default: customer-support-{env})"
    )
    parser.add_argument(
        "--service",
        help="ECS service name (default: customer-support-api-{env})"
    )

    args = parser.parse_args()

    # Validate AWS credentials
    try:
        boto3.client("sts").get_caller_identity()
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("Configure with: aws configure")
        sys.exit(1)

    # Create deployer and execute
    deployer = ECSDeployer(
        region=args.region,
        environment=args.env,
        cluster_name=args.cluster,
        service_name=args.service
    )

    success = deployer.deploy()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
