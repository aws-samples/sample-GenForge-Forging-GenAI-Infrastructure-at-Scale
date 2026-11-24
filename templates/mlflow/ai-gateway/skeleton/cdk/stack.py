"""MLflow AI Gateway on ECS Fargate - CDK Stack.

This stack provisions a reference MLflow AI Gateway deployment:
- ECR Repository for the MLflow container image
- S3 Bucket for ML artifact storage (SSE-KMS, versioning)
- DynamoDB Table for experiment tracking metadata (PAY_PER_REQUEST)
- ECS Fargate Cluster & Service with ALB
- Application Load Balancer (public-facing, HTTP on port 80)
- IAM roles (task role + execution role) with least-privilege access
- Security Groups (ALB allows inbound 80; ECS allows traffic from ALB only)
- Auto Scaling (target-tracking on CPU utilization at 70%)
- CloudWatch Log Group for container logs
"""

from typing import Any, Optional
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    RemovalPolicy,
    Duration,
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_logs as logs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from constructs import Construct


class MlflowAiGatewayStack(Stack):
    """CDK stack for MLflow AI Gateway on ECS Fargate."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        environment: str,
        vpc_id: str,
        private_subnet_ids: str,
        public_subnet_ids: str,
        certificate_arn: str,
        backend_store_type: str = "dynamodb",
        artifact_bucket_name: Optional[str] = None,
        container_cpu: int = 512,
        container_memory: int = 1024,
        desired_count: int = 2,
        enable_auto_scaling: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal_policy = (
            RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # -------------------------------------------------------------------
        # Networking - Import existing VPC and subnets
        # -------------------------------------------------------------------
        vpc = ec2.Vpc.from_lookup(
            self,
            "ImportedVpc",
            vpc_id=vpc_id,
        )

        private_subnets = [
            ec2.Subnet.from_subnet_id(self, f"PrivateSubnet{i}", subnet_id.strip())
            for i, subnet_id in enumerate(private_subnet_ids.split(","))
        ]

        public_subnets = [
            ec2.Subnet.from_subnet_id(self, f"PublicSubnet{i}", subnet_id.strip())
            for i, subnet_id in enumerate(public_subnet_ids.split(","))
        ]

        # -------------------------------------------------------------------
        # ECR Repository - Import existing repository created by workflow
        # -------------------------------------------------------------------
        ecr_repository = ecr.Repository.from_repository_name(
            self,
            "MlflowEcrRepository",
            repository_name=f"{component_name}-{environment}-mlflow",
        )

        # -------------------------------------------------------------------
        # S3 Bucket for ML Artifacts
        # -------------------------------------------------------------------
        bucket_name = artifact_bucket_name or f"{component_name}-{environment}-artifacts-{self.account}"
        artifact_bucket = s3.Bucket(
            self,
            "ArtifactBucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=removal_policy,
            auto_delete_objects=(environment == "dev"),
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(90),
                        )
                    ],
                )
            ],
        )

        # -------------------------------------------------------------------
        # DynamoDB Table for Experiment Tracking
        # -------------------------------------------------------------------
        tracking_table = dynamodb.Table(
            self,
            "TrackingTable",
            table_name=f"{component_name}-{environment}-tracking",
            partition_key=dynamodb.Attribute(
                name="experiment_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="run_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=removal_policy,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )

        # Add GSI for querying by run status
        tracking_table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="start_time",
                type=dynamodb.AttributeType.NUMBER,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # -------------------------------------------------------------------
        # CloudWatch Log Group
        # -------------------------------------------------------------------
        log_group = logs.LogGroup(
            self,
            "MlflowLogGroup",
            log_group_name=f"/genforge/{component_name}-{environment}/mlflow-gateway",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
        )

        # -------------------------------------------------------------------
        # ECS Cluster
        # -------------------------------------------------------------------
        cluster = ecs.Cluster(
            self,
            "MlflowCluster",
            cluster_name=f"{component_name}-{environment}-cluster",
            vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.ENABLED,
        )

        # -------------------------------------------------------------------
        # IAM Task Execution Role (ECR pull, CloudWatch logs)
        # -------------------------------------------------------------------
        execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            role_name=f"{component_name}-{environment}-exec-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="ECS task execution role for MLflow AI Gateway",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        # -------------------------------------------------------------------
        # IAM Task Role (S3, DynamoDB, Bedrock access)
        # -------------------------------------------------------------------
        task_role = iam.Role(
            self,
            "TaskRole",
            role_name=f"{component_name}-{environment}-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="ECS task role for MLflow AI Gateway with S3, DynamoDB, and Bedrock access",
        )

        # S3 permissions for artifact storage
        artifact_bucket.grant_read_write(task_role)

        # DynamoDB permissions for experiment tracking
        tracking_table.grant_read_write_data(task_role)

        # Bedrock permissions for AI Gateway routes
        task_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAccess",
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:ListFoundationModels",
                    "bedrock:GetFoundationModel",
                ],
                resources=["*"],
            )
        )

        # -------------------------------------------------------------------
        # Security Groups
        # -------------------------------------------------------------------
        alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            security_group_name=f"{component_name}-{environment}-alb-sg",
            description="Security group for MLflow AI Gateway ALB",
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS inbound",
        )
        alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP inbound (redirected to HTTPS at the listener)",
        )

        ecs_sg = ec2.SecurityGroup(
            self,
            "EcsSecurityGroup",
            vpc=vpc,
            security_group_name=f"{component_name}-{environment}-ecs-sg",
            description="Security group for MLflow ECS tasks",
            allow_all_outbound=True,
        )
        ecs_sg.add_ingress_rule(
            alb_sg,
            ec2.Port.tcp(5000),
            "Allow traffic from ALB to MLflow",
        )

        # -------------------------------------------------------------------
        # ECS Task Definition
        # -------------------------------------------------------------------
        task_definition = ecs.FargateTaskDefinition(
            self,
            "MlflowTaskDef",
            family=f"{component_name}-{environment}-mlflow",
            cpu=container_cpu,
            memory_limit_mib=container_memory,
            execution_role=execution_role,
            task_role=task_role,
        )

        container = task_definition.add_container(
            "MlflowContainer",
            image=ecs.ContainerImage.from_ecr_repository(ecr_repository, tag="latest"),
            container_name="mlflow",
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="mlflow",
                log_group=log_group,
            ),
            environment={
                "MLFLOW_BACKEND_STORE_URI": f"dynamodb://{tracking_table.table_name}",
                "MLFLOW_ARTIFACT_ROOT": f"s3://{artifact_bucket.bucket_name}/artifacts",
                "AWS_DEFAULT_REGION": self.region,
                "MLFLOW_HOST": "0.0.0.0",
                "MLFLOW_PORT": "5000",
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )

        container.add_port_mappings(
            ecs.PortMapping(
                container_port=5000,
                protocol=ecs.Protocol.TCP,
            )
        )

        # -------------------------------------------------------------------
        # Application Load Balancer
        # -------------------------------------------------------------------
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "MlflowAlb",
            load_balancer_name=f"{component_name}-{environment}-alb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnets=public_subnets),
        )

        # -------------------------------------------------------------------
        # ECS Fargate Service
        # -------------------------------------------------------------------
        fargate_service = ecs.FargateService(
            self,
            "MlflowService",
            service_name=f"{component_name}-{environment}-svc",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=desired_count,
            security_groups=[ecs_sg],
            vpc_subnets=ec2.SubnetSelection(subnets=private_subnets),
            assign_public_ip=False,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

        # -------------------------------------------------------------------
        # ALB Target Group & Listeners
        # -------------------------------------------------------------------
        # Primary HTTPS listener. TLS is terminated at the ALB using an
        # ACM certificate; traffic between the ALB and Fargate stays inside
        # the VPC.
        https_listener = alb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[elbv2.ListenerCertificate.of(certificate_arn)],
            ssl_policy=elbv2.SslPolicy.TLS12_EXT,
        )

        target_group = https_listener.add_targets(
            "MlflowTargets",
            port=5000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[fargate_service],
            health_check=elbv2.HealthCheck(
                path="/health",
                port="5000",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        # Redirect all plain HTTP traffic to HTTPS.
        alb.add_listener(
            "HttpRedirectListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.redirect(
                protocol="HTTPS",
                port="443",
                permanent=True,
            ),
        )

        # -------------------------------------------------------------------
        # Auto Scaling
        # -------------------------------------------------------------------
        if enable_auto_scaling:
            scalable_target = fargate_service.auto_scale_task_count(
                min_capacity=desired_count,
                max_capacity=desired_count * 3,
            )

            scalable_target.scale_on_cpu_utilization(
                "CpuScaling",
                target_utilization_percent=70,
                scale_in_cooldown=Duration.seconds(300),
                scale_out_cooldown=Duration.seconds(60),
            )

        # -------------------------------------------------------------------
        # Tags
        # -------------------------------------------------------------------
        Tags.of(self).add("Name", f"{component_name}-{environment}-mlflow-gateway")
        Tags.of(self).add("environment", environment)
        Tags.of(self).add("owner", kwargs.get("tags", {}).get("owner", "platform-team"))
        Tags.of(self).add("genforge:managed", "true")

        # -------------------------------------------------------------------
        # Outputs
        # -------------------------------------------------------------------
        CfnOutput(
            self,
            "AlbDnsName",
            value=alb.load_balancer_dns_name,
            description="Application Load Balancer DNS name for MLflow UI",
            export_name=f"{construct_id}-alb-dns",
        )

        CfnOutput(
            self,
            "MlflowUrl",
            value=f"https://{alb.load_balancer_dns_name}",
            description="MLflow AI Gateway URL (TLS terminated at the ALB)",
            export_name=f"{construct_id}-mlflow-url",
        )

        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=ecr_repository.repository_uri,
            description="ECR repository URI for MLflow container image",
            export_name=f"{construct_id}-ecr-repo-uri",
        )

        CfnOutput(
            self,
            "ArtifactBucketName",
            value=artifact_bucket.bucket_name,
            description="S3 bucket for ML artifacts",
            export_name=f"{construct_id}-artifact-bucket",
        )

        CfnOutput(
            self,
            "TrackingTableName",
            value=tracking_table.table_name,
            description="DynamoDB table for experiment tracking",
            export_name=f"{construct_id}-tracking-table",
        )

        CfnOutput(
            self,
            "EcsClusterName",
            value=cluster.cluster_name,
            description="ECS cluster name",
            export_name=f"{construct_id}-ecs-cluster",
        )

        CfnOutput(
            self,
            "EcsServiceName",
            value=fargate_service.service_name,
            description="ECS Fargate service name",
            export_name=f"{construct_id}-ecs-service",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="CloudWatch Log Group for MLflow container logs",
            export_name=f"{construct_id}-log-group",
        )
