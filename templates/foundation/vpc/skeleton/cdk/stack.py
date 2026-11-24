"""VPC Foundation CDK Stack for GenForge.

Creates a multi-tier VPC with public, private, and isolated subnets,
NAT gateways, VPC flow logs, and VPC endpoints for GenAI services.
"""

from typing import Any

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    Tags,
    aws_ec2 as ec2,
    aws_logs as logs,
)
from constructs import Construct


class VpcStack(Stack):
    """AWS VPC Stack optimized for GenAI workloads.

    Creates a VPC with public, private, and isolated subnets across multiple
    availability zones. Includes NAT gateways for private subnet internet
    access, VPC flow logs for network monitoring, and VPC endpoints for
    AWS services commonly used in GenAI workloads (SageMaker, Bedrock, S3, ECR).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        environment: str,
        vpc_cidr: str,
        availability_zones: int,
        enable_nat_gateway: bool,
        single_nat_gateway: bool,
        enable_vpc_endpoints: bool,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._component_name = component_name
        self._environment = environment
        self._resource_prefix = f"{component_name}-{environment}"

        # Determine removal policy based on environment
        self._removal_policy = (
            RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Determine NAT gateway configuration
        nat_gateways = 0
        if enable_nat_gateway:
            nat_gateways = 1 if single_nat_gateway else availability_zones

        # -------------------------------------------------------------------
        # VPC
        # -------------------------------------------------------------------
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=self._resource_prefix,
            ip_addresses=ec2.IpAddresses.cidr(vpc_cidr),
            max_azs=availability_zones,
            nat_gateways=nat_gateways,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            restrict_default_security_group=True,
        )

        # -------------------------------------------------------------------
        # VPC Flow Logs
        # -------------------------------------------------------------------
        flow_log_group = logs.LogGroup(
            self,
            "FlowLogGroup",
            log_group_name=f"/genforge/{self._resource_prefix}/vpc-flow-logs",
            retention=logs.RetentionDays.ONE_MONTH if environment == "dev" else logs.RetentionDays.SIX_MONTHS,
            removal_policy=self._removal_policy,
        )

        self.vpc.add_flow_log(
            "FlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_log_group),
            traffic_type=ec2.FlowLogTrafficType.ALL,
        )

        # -------------------------------------------------------------------
        # VPC Endpoints
        # -------------------------------------------------------------------
        if enable_vpc_endpoints:
            self._create_vpc_endpoints()

        # -------------------------------------------------------------------
        # Tags
        # -------------------------------------------------------------------
        Tags.of(self).add("Name", self._resource_prefix)
        Tags.of(self).add("environment", environment)
        Tags.of(self).add("owner", tags.get("owner", "platform-team") if tags else "platform-team")
        Tags.of(self).add("genforge:managed", "true")

        # Apply any additional tags passed from the app
        if tags:
            for key, value in tags.items():
                Tags.of(self).add(key, value)

        # -------------------------------------------------------------------
        # Outputs
        # -------------------------------------------------------------------
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self._resource_prefix}-vpc-id",
        )

        CfnOutput(
            self,
            "VpcCidr",
            value=self.vpc.vpc_cidr_block,
            description="VPC CIDR Block",
            export_name=f"{self._resource_prefix}-vpc-cidr",
        )

        public_subnet_ids = [subnet.subnet_id for subnet in self.vpc.public_subnets]
        CfnOutput(
            self,
            "PublicSubnetIds",
            value=",".join(public_subnet_ids),
            description="Public Subnet IDs (comma-separated)",
            export_name=f"{self._resource_prefix}-public-subnet-ids",
        )

        private_subnet_ids = [subnet.subnet_id for subnet in self.vpc.private_subnets]
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join(private_subnet_ids),
            description="Private Subnet IDs (comma-separated)",
            export_name=f"{self._resource_prefix}-private-subnet-ids",
        )

        isolated_subnet_ids = [subnet.subnet_id for subnet in self.vpc.isolated_subnets]
        CfnOutput(
            self,
            "IsolatedSubnetIds",
            value=",".join(isolated_subnet_ids),
            description="Isolated Subnet IDs (comma-separated)",
            export_name=f"{self._resource_prefix}-isolated-subnet-ids",
        )

    def _create_vpc_endpoints(self) -> None:
        """Create VPC endpoints for AWS services used in GenAI workloads."""

        # ------------------------------------------------------------------
        # Gateway endpoints (no cost)
        # ------------------------------------------------------------------
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )

        # ------------------------------------------------------------------
        # Security group for interface endpoints
        # ------------------------------------------------------------------
        endpoint_sg = ec2.SecurityGroup(
            self,
            "VpcEndpointSG",
            vpc=self.vpc,
            security_group_name=f"{self._resource_prefix}-vpc-endpoints-sg",
            description="Security group for VPC interface endpoints",
            allow_all_outbound=True,
        )
        endpoint_sg.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            "Allow HTTPS from VPC CIDR",
        )

        # ------------------------------------------------------------------
        # Interface endpoints for GenAI and core AWS services
        # ------------------------------------------------------------------
        interface_endpoints: list[tuple[str, ec2.InterfaceVpcEndpointAwsService]] = [
            # SageMaker services
            ("SageMakerApi", ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API),
            ("SageMakerRuntime", ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME),
            # Bedrock services
            ("Bedrock", ec2.InterfaceVpcEndpointAwsService("bedrock")),
            ("BedrockRuntime", ec2.InterfaceVpcEndpointAwsService("bedrock-runtime")),
            # Container services
            ("EcrApi", ec2.InterfaceVpcEndpointAwsService.ECR),
            ("EcrDocker", ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER),
            # Monitoring and logging
            ("CloudWatchLogs", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS),
            # Management and security
            ("Ssm", ec2.InterfaceVpcEndpointAwsService.SSM),
            ("Sts", ec2.InterfaceVpcEndpointAwsService.STS),
            ("Kms", ec2.InterfaceVpcEndpointAwsService.KMS),
            ("SecretsManager", ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER),
        ]

        endpoint_ids: list[str] = []

        for endpoint_name, service in interface_endpoints:
            endpoint = self.vpc.add_interface_endpoint(
                endpoint_name,
                service=service,
                subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                security_groups=[endpoint_sg],
                private_dns_enabled=True,
            )
            endpoint_ids.append(endpoint_name)

        # Output the list of created VPC endpoint names
        CfnOutput(
            self,
            "VpcEndpoints",
            value=",".join(endpoint_ids),
            description="VPC Interface Endpoints created (names)",
            export_name=f"{self._resource_prefix}-vpc-endpoints",
        )

        CfnOutput(
            self,
            "VpcEndpointSecurityGroupId",
            value=endpoint_sg.security_group_id,
            description="Security Group ID for VPC endpoints",
            export_name=f"{self._resource_prefix}-vpc-endpoint-sg-id",
        )
