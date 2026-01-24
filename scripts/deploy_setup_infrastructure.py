#!/usr/bin/env python3
"""
AWS ECS Infrastructure Setup Script

Creates the required AWS infrastructure for ECS deployment:
- VPC, Subnets, Security Groups (optional)
- ECS Cluster
- Application Load Balancer
- Target Group
- ECS Service
- Auto Scaling (optional)

Usage:
    # Use existing VPC
    python scripts/deploy_setup_infrastructure.py --env production --region us-east-1 --vpc-id vpc-xxx

    # Create new VPC
    python scripts/deploy_setup_infrastructure.py --env production --region us-east-1 --create-vpc

Prerequisites:
    - AWS CLI configured
    - boto3 installed
    - IAM roles: ecsTaskExecutionRole, ecsTaskRole
"""

import argparse
import sys
import time
from typing import List, Dict, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


class ECSInfrastructureSetup:
    """AWS ECS infrastructure orchestrator"""

    def __init__(self, region: str, environment: str):
        self.region = region
        self.environment = environment
        self.cluster_name = f"customer-support-{environment}"
        self.service_name = f"customer-support-api-{environment}"

        # AWS clients
        self.ec2 = boto3.client("ec2", region_name=region)
        self.ecs = boto3.client("ecs", region_name=region)
        self.elbv2 = boto3.client("elbv2", region_name=region)
        self.autoscaling = boto3.client("application-autoscaling", region_name=region)

        # Get account ID
        sts = boto3.client("sts")
        self.account_id = sts.get_caller_identity()["Account"]

    def create_vpc(self) -> Dict[str, Any]:
        """Create VPC with public and private subnets"""
        print("\n[1/7] Creating VPC...")

        # Create VPC
        vpc = self.ec2.create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[{
                "ResourceType": "vpc",
                "Tags": [
                    {"Key": "Name", "Value": f"customer-support-{self.environment}"},
                    {"Key": "Environment", "Value": self.environment}
                ]
            }]
        )
        vpc_id = vpc["Vpc"]["VpcId"]
        print(f"✓ Created VPC: {vpc_id}")

        # Enable DNS
        self.ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
        self.ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})

        # Create Internet Gateway
        igw = self.ec2.create_internet_gateway(
            TagSpecifications=[{
                "ResourceType": "internet-gateway",
                "Tags": [{"Key": "Name", "Value": f"customer-support-{self.environment}"}]
            }]
        )
        igw_id = igw["InternetGateway"]["InternetGatewayId"]
        self.ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        print(f"✓ Created Internet Gateway: {igw_id}")

        # Get availability zones
        azs = self.ec2.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}]
        )["AvailabilityZones"][:2]

        # Create public subnets
        public_subnets = []
        for i, az in enumerate(azs):
            subnet = self.ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=f"10.0.{i}.0/24",
                AvailabilityZone=az["ZoneName"],
                TagSpecifications=[{
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "Name", "Value": f"customer-support-public-{i+1}"},
                        {"Key": "Type", "Value": "public"}
                    ]
                }]
            )
            subnet_id = subnet["Subnet"]["SubnetId"]
            public_subnets.append(subnet_id)

            # Enable auto-assign public IP
            self.ec2.modify_subnet_attribute(
                SubnetId=subnet_id,
                MapPublicIpOnLaunch={"Value": True}
            )
            print(f"✓ Created public subnet: {subnet_id} ({az['ZoneName']})")

        # Create route table for public subnets
        route_table = self.ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=[{
                "ResourceType": "route-table",
                "Tags": [{"Key": "Name", "Value": f"customer-support-public"}]
            }]
        )
        route_table_id = route_table["RouteTable"]["RouteTableId"]

        # Add route to internet gateway
        self.ec2.create_route(
            RouteTableId=route_table_id,
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=igw_id
        )

        # Associate route table with subnets
        for subnet_id in public_subnets:
            self.ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)

        print(f"✓ VPC setup complete")

        return {
            "vpc_id": vpc_id,
            "subnet_ids": public_subnets,
            "igw_id": igw_id
        }

    def create_security_groups(self, vpc_id: str) -> Dict[str, str]:
        """Create security groups for ALB and ECS tasks"""
        print("\n[2/7] Creating security groups...")

        # ALB Security Group
        alb_sg = self.ec2.create_security_group(
            GroupName=f"customer-support-alb-{self.environment}",
            Description="Security group for ALB",
            VpcId=vpc_id,
            TagSpecifications=[{
                "ResourceType": "security-group",
                "Tags": [{"Key": "Name", "Value": f"customer-support-alb-{self.environment}"}]
            }]
        )
        alb_sg_id = alb_sg["GroupId"]

        # Allow HTTP/HTTPS from internet
        self.ec2.authorize_security_group_ingress(
            GroupId=alb_sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP from internet"}]
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS from internet"}]
                }
            ]
        )
        print(f"✓ Created ALB security group: {alb_sg_id}")

        # ECS Tasks Security Group
        ecs_sg = self.ec2.create_security_group(
            GroupName=f"customer-support-ecs-{self.environment}",
            Description="Security group for ECS tasks",
            VpcId=vpc_id,
            TagSpecifications=[{
                "ResourceType": "security-group",
                "Tags": [{"Key": "Name", "Value": f"customer-support-ecs-{self.environment}"}]
            }]
        )
        ecs_sg_id = ecs_sg["GroupId"]

        # Allow traffic from ALB
        self.ec2.authorize_security_group_ingress(
            GroupId=ecs_sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 8000,
                "ToPort": 8000,
                "UserIdGroupPairs": [{"GroupId": alb_sg_id, "Description": "From ALB"}]
            }]
        )
        print(f"✓ Created ECS security group: {ecs_sg_id}")

        return {
            "alb_sg_id": alb_sg_id,
            "ecs_sg_id": ecs_sg_id
        }

    def create_ecs_cluster(self) -> str:
        """Create ECS cluster"""
        print(f"\n[3/7] Creating ECS cluster: {self.cluster_name}")

        try:
            response = self.ecs.create_cluster(
                clusterName=self.cluster_name,
                capacityProviders=["FARGATE", "FARGATE_SPOT"],
                defaultCapacityProviderStrategy=[
                    {"capacityProvider": "FARGATE", "weight": 1, "base": 1}
                ],
                tags=[
                    {"key": "Environment", "value": self.environment},
                    {"key": "Application", "value": "customer-support-multiagent"}
                ]
            )
            cluster_arn = response["cluster"]["clusterArn"]
            print(f"✓ Created cluster: {cluster_arn}")
            return cluster_arn
        except ClientError as e:
            if "ClusterAlreadyExists" in str(e):
                print(f"✓ Cluster already exists: {self.cluster_name}")
                response = self.ecs.describe_clusters(clusters=[self.cluster_name])
                return response["clusters"][0]["clusterArn"]
            raise

    def create_load_balancer(self, vpc_id: str, subnet_ids: List[str], sg_id: str) -> Dict[str, str]:
        """Create Application Load Balancer"""
        print("\n[4/7] Creating Application Load Balancer...")

        # Create ALB
        alb = self.elbv2.create_load_balancer(
            Name=f"cs-{self.environment}",  # max 32 chars
            Subnets=subnet_ids,
            SecurityGroups=[sg_id],
            Scheme="internet-facing",
            Type="application",
            IpAddressType="ipv4",
            Tags=[
                {"Key": "Environment", "Value": self.environment},
                {"Key": "Application", "Value": "customer-support"}
            ]
        )
        alb_arn = alb["LoadBalancers"][0]["LoadBalancerArn"]
        alb_dns = alb["LoadBalancers"][0]["DNSName"]
        print(f"✓ Created ALB: {alb_dns}")

        # Create Target Group
        tg = self.elbv2.create_target_group(
            Name=f"cs-tg-{self.environment}",
            Protocol="HTTP",
            Port=8000,
            VpcId=vpc_id,
            TargetType="ip",  # For Fargate
            HealthCheckEnabled=True,
            HealthCheckPath="/api/health",
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=3,
            Tags=[
                {"Key": "Environment", "Value": self.environment}
            ]
        )
        tg_arn = tg["TargetGroups"][0]["TargetGroupArn"]
        print(f"✓ Created Target Group: {tg_arn}")

        # Create Listener
        listener = self.elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[{
                "Type": "forward",
                "TargetGroupArn": tg_arn
            }]
        )
        print(f"✓ Created Listener (HTTP:80 -> Target Group)")

        return {
            "alb_arn": alb_arn,
            "alb_dns": alb_dns,
            "target_group_arn": tg_arn
        }

    def create_ecs_service(
        self,
        cluster_arn: str,
        task_definition: str,
        subnet_ids: List[str],
        sg_id: str,
        target_group_arn: str
    ):
        """Create ECS service"""
        print(f"\n[5/7] Creating ECS service: {self.service_name}")

        try:
            response = self.ecs.create_service(
                cluster=cluster_arn,
                serviceName=self.service_name,
                taskDefinition=task_definition,
                desiredCount=1,
                launchType="FARGATE",
                platformVersion="LATEST",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnet_ids,
                        "securityGroups": [sg_id],
                        "assignPublicIp": "ENABLED"
                    }
                },
                loadBalancers=[{
                    "targetGroupArn": target_group_arn,
                    "containerName": "api",
                    "containerPort": 8000
                }],
                healthCheckGracePeriodSeconds=60,
                deploymentConfiguration={
                    "maximumPercent": 200,
                    "minimumHealthyPercent": 100,
                    "deploymentCircuitBreaker": {
                        "enable": True,
                        "rollback": True
                    }
                },
                tags=[
                    {"key": "Environment", "value": self.environment}
                ]
            )
            print(f"✓ Created service: {self.service_name}")
            return response["service"]["serviceArn"]
        except ClientError as e:
            if "ServiceAlreadyExists" in str(e):
                print(f"✓ Service already exists: {self.service_name}")
                return None
            raise

    def setup_autoscaling(self, cluster_name: str, service_name: str):
        """Setup auto scaling for ECS service"""
        print("\n[6/7] Setting up auto scaling...")

        resource_id = f"service/{cluster_name}/{service_name}"

        # Register scalable target
        try:
            self.autoscaling.register_scalable_target(
                ServiceNamespace="ecs",
                ResourceId=resource_id,
                ScalableDimension="ecs:service:DesiredCount",
                MinCapacity=1,
                MaxCapacity=10
            )
            print(f"✓ Registered scalable target (min: 1, max: 10)")

            # CPU-based scaling policy
            self.autoscaling.put_scaling_policy(
                PolicyName=f"{service_name}-cpu-scaling",
                ServiceNamespace="ecs",
                ResourceId=resource_id,
                ScalableDimension="ecs:service:DesiredCount",
                PolicyType="TargetTrackingScaling",
                TargetTrackingScalingPolicyConfiguration={
                    "TargetValue": 70.0,
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
                    },
                    "ScaleOutCooldown": 60,
                    "ScaleInCooldown": 180
                }
            )
            print(f"✓ Created CPU-based scaling policy (target: 70%)")

        except ClientError as e:
            print(f"⚠ Auto scaling setup warning: {e}")

    def print_summary(self, resources: Dict[str, Any]):
        """Print deployment summary"""
        print("\n" + "=" * 60)
        print("✓ INFRASTRUCTURE SETUP COMPLETE")
        print("=" * 60)

        print(f"\nEnvironment: {self.environment}")
        print(f"Region: {self.region}")

        if "vpc_id" in resources:
            print(f"\nVPC: {resources['vpc_id']}")
            print(f"Subnets: {', '.join(resources['subnet_ids'])}")

        if "alb_dns" in resources:
            print(f"\nLoad Balancer URL: http://{resources['alb_dns']}")
            print(f"Health Check: http://{resources['alb_dns']}/api/health")

        print(f"\nECS Cluster: {self.cluster_name}")
        print(f"ECS Service: {self.service_name}")

        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("\n1. Setup secrets:")
        print(f"   python scripts/deploy_setup_secrets.py --env {self.environment} --interactive")
        print("\n2. Deploy application:")
        print(f"   python scripts/deploy_ecs.py --env {self.environment}")
        print("\n3. Access application:")
        if "alb_dns" in resources:
            print(f"   http://{resources['alb_dns']}/docs")


def main():
    parser = argparse.ArgumentParser(
        description="Setup AWS ECS infrastructure for Customer Support system"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["development", "staging", "production"],
        help="Environment to setup"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    parser.add_argument(
        "--create-vpc",
        action="store_true",
        help="Create new VPC and subnets"
    )
    parser.add_argument(
        "--vpc-id",
        help="Use existing VPC ID"
    )
    parser.add_argument(
        "--subnet-ids",
        help="Comma-separated subnet IDs (required if using existing VPC)"
    )
    parser.add_argument(
        "--task-definition",
        default="customer-support-production:1",
        help="Task definition to use (default: customer-support-production:1)"
    )

    args = parser.parse_args()

    if not args.create_vpc and not args.vpc_id:
        print("ERROR: Specify --create-vpc or --vpc-id")
        sys.exit(1)

    # Validate AWS credentials
    try:
        boto3.client("sts").get_caller_identity()
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        sys.exit(1)

    # Create setup instance
    setup = ECSInfrastructureSetup(region=args.region, environment=args.env)

    resources = {}

    try:
        # Step 1-2: VPC and Security Groups
        if args.create_vpc:
            vpc_resources = setup.create_vpc()
            resources.update(vpc_resources)
            sg_resources = setup.create_security_groups(vpc_resources["vpc_id"])
            resources.update(sg_resources)
        else:
            resources["vpc_id"] = args.vpc_id
            resources["subnet_ids"] = args.subnet_ids.split(",")
            sg_resources = setup.create_security_groups(args.vpc_id)
            resources.update(sg_resources)

        # Step 3: ECS Cluster
        cluster_arn = setup.create_ecs_cluster()
        resources["cluster_arn"] = cluster_arn

        # Step 4: Load Balancer
        lb_resources = setup.create_load_balancer(
            resources["vpc_id"],
            resources["subnet_ids"],
            resources["alb_sg_id"]
        )
        resources.update(lb_resources)

        # Step 5: ECS Service
        service_arn = setup.create_ecs_service(
            cluster_arn,
            args.task_definition,
            resources["subnet_ids"],
            resources["ecs_sg_id"],
            resources["target_group_arn"]
        )

        # Step 6: Auto Scaling
        if service_arn:
            setup.setup_autoscaling(setup.cluster_name, setup.service_name)

        # Step 7: Summary
        setup.print_summary(resources)

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
