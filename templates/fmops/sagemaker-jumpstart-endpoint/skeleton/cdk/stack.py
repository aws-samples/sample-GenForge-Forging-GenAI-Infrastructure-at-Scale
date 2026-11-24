"""SageMaker JumpStart Endpoint CDK Stack.

This stack provisions:
- IAM role for SageMaker with necessary permissions
- SageMaker Model (using JumpStart model package ARN pattern)
- SageMaker EndpointConfig (instance type, optional data capture)
- SageMaker Endpoint (real-time inference)
- S3 bucket for data capture (if enabled)
- CloudWatch alarms (5XX errors, model latency, invocations per instance)
"""

from typing import Any
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    RemovalPolicy,
)
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct


# JumpStart model package ARN mapping per region
# Format: arn:aws:sagemaker:<region>:aws:model-package/<model-package-name>
JUMPSTART_REGION_MAP = {
    "us-east-1": "865070037744",
    "us-west-2": "594846645681",
    "eu-west-1": "985815980388",
}


class SageMakerJumpStartEndpointStack(Stack):
    """SageMaker JumpStart Foundation Model Endpoint."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        jumpstart_model_id: str,
        instance_type: str = "ml.g5.xlarge",
        initial_instance_count: int = 1,
        enable_data_capture: bool = False,
        data_capture_percent: int = 10,
        environment: str = "dev",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        auto_delete = environment == "dev"
        endpoint_name = f"{component_name}-{environment}-endpoint"

        # ------------------------------------------------------------------ #
        # KMS Key
        # ------------------------------------------------------------------ #
        encryption_key = kms.Key(
            self,
            "EncryptionKey",
            alias=f"{component_name}-{environment}-jumpstart-key",
            enable_key_rotation=True,
            removal_policy=removal,
            description=f"Encryption key for {component_name} JumpStart endpoint",
        )

        # ------------------------------------------------------------------ #
        # IAM role — SageMaker execution
        # ------------------------------------------------------------------ #
        # Least-privilege replacement for the AmazonSageMakerFullAccess managed
        # policy. Scoped to the endpoint/model/config this stack creates plus
        # dependencies SageMaker needs at inference time (ECR pull, CloudWatch
        # logs and metrics).
        sagemaker_role = iam.Role(
            self,
            "SageMakerExecutionRole",
            role_name=f"{component_name}-{environment}-sagemaker-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description=(
                f"Scoped SageMaker execution role for {component_name} "
                f"JumpStart endpoint - no managed policies attached."
            ),
        )

        # SageMaker inference-time APIs scoped to this stack's resources.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="SageMakerRuntime",
                actions=[
                    "sagemaker:InvokeEndpoint",
                    "sagemaker:DescribeEndpoint",
                    "sagemaker:DescribeEndpointConfig",
                    "sagemaker:DescribeModel",
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{component_name}-{environment}-*",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint-config/{component_name}-{environment}-*",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model/{component_name}-{environment}-*",
                ],
            )
        )

        # JumpStart model package image pull.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImagePull",
                actions=[
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=[
                    # JumpStart model package images live in AWS-managed accounts per region.
                    f"arn:aws:ecr:{self.region}:*:repository/*",
                ],
            )
        )

        # Endpoint log group and metrics.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="EndpointLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/Endpoints*",
                ],
            )
        )

        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="EndpointMetrics",
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "cloudwatch:namespace": ["AWS/SageMaker", "/aws/sagemaker"],
                    }
                },
            )
        )

        # ------------------------------------------------------------------ #
        # S3 bucket — data capture (conditional)
        # ------------------------------------------------------------------ #
        data_capture_bucket = None
        if enable_data_capture:
            data_capture_bucket = s3.Bucket(
                self,
                "DataCaptureBucket",
                bucket_name=f"{component_name}-{environment}-data-capture-{self.account}",
                encryption=s3.BucketEncryption.KMS,
                encryption_key=encryption_key,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=removal,
                auto_delete_objects=auto_delete,
                enforce_ssl=True,
            )
            data_capture_bucket.grant_write(sagemaker_role)

        # ------------------------------------------------------------------ #
        # SageMaker Model
        # ------------------------------------------------------------------ #
        # JumpStart models use the model package group ARN pattern
        jumpstart_account = JUMPSTART_REGION_MAP.get(self.region, "865070037744")

        model = sagemaker.CfnModel(
            self,
            "JumpStartModel",
            model_name=f"{component_name}-{environment}-model",
            execution_role_arn=sagemaker_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                model_package_name=(
                    f"arn:aws:sagemaker:{self.region}:{jumpstart_account}:"
                    f"model-package/{jumpstart_model_id}"
                ),
            ),
        )

        # ------------------------------------------------------------------ #
        # SageMaker EndpointConfig
        # ------------------------------------------------------------------ #
        endpoint_config_props: dict = {
            "endpoint_config_name": f"{component_name}-{environment}-config",
            "production_variants": [
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    model_name=model.model_name or f"{component_name}-{environment}-model",
                    instance_type=instance_type,
                    initial_instance_count=initial_instance_count,
                    initial_variant_weight=1.0,
                ),
            ],
            "kms_key_id": encryption_key.key_id,
        }

        if enable_data_capture and data_capture_bucket:
            endpoint_config_props["data_capture_config"] = (
                sagemaker.CfnEndpointConfig.DataCaptureConfigProperty(
                    enable_capture=True,
                    initial_sampling_percentage=data_capture_percent,
                    destination_s3_uri=f"s3://{data_capture_bucket.bucket_name}/capture",
                    capture_options=[
                        sagemaker.CfnEndpointConfig.CaptureOptionProperty(
                            capture_mode="Input"
                        ),
                        sagemaker.CfnEndpointConfig.CaptureOptionProperty(
                            capture_mode="Output"
                        ),
                    ],
                )
            )

        endpoint_config = sagemaker.CfnEndpointConfig(
            self, "EndpointConfig", **endpoint_config_props
        )
        endpoint_config.add_dependency(model)

        # ------------------------------------------------------------------ #
        # SageMaker Endpoint
        # ------------------------------------------------------------------ #
        endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_name=endpoint_name,
            endpoint_config_name=(
                endpoint_config.endpoint_config_name
                or f"{component_name}-{environment}-config"
            ),
        )
        endpoint.add_dependency(endpoint_config)

        # ------------------------------------------------------------------ #
        # CloudWatch Alarms
        # ------------------------------------------------------------------ #
        cloudwatch.Alarm(
            self,
            "Invocation5XXErrorsAlarm",
            alarm_name=f"{component_name}-{environment}-5xx-errors",
            metric=cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="Invocation5XXErrors",
                dimensions_map={"EndpointName": endpoint_name, "VariantName": "AllTraffic"},
                statistic="Sum",
                period=cdk.Duration.minutes(5),
            ),
            evaluation_periods=2,
            threshold=5,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when 5XX errors exceed threshold",
        )

        cloudwatch.Alarm(
            self,
            "ModelLatencyAlarm",
            alarm_name=f"{component_name}-{environment}-latency",
            metric=cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="ModelLatency",
                dimensions_map={"EndpointName": endpoint_name, "VariantName": "AllTraffic"},
                statistic="Average",
                period=cdk.Duration.minutes(5),
            ),
            evaluation_periods=3,
            threshold=30000000,  # 30 seconds in microseconds
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when model latency exceeds 30s",
        )

        cloudwatch.Alarm(
            self,
            "InvocationsPerInstanceAlarm",
            alarm_name=f"{component_name}-{environment}-invocations",
            metric=cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="InvocationsPerInstance",
                dimensions_map={"EndpointName": endpoint_name, "VariantName": "AllTraffic"},
                statistic="Sum",
                period=cdk.Duration.minutes(5),
            ),
            evaluation_periods=3,
            threshold=1000,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description="Alarm when invocations per instance is high",
        )

        # ------------------------------------------------------------------ #
        # Tags
        # ------------------------------------------------------------------ #
        Tags.of(self).add("Name", component_name)
        Tags.of(self).add("environment", environment)
        Tags.of(self).add("owner", component_name)
        Tags.of(self).add("genforge:managed", "true")

        # ------------------------------------------------------------------ #
        # Outputs
        # ------------------------------------------------------------------ #
        CfnOutput(
            self, "EndpointName",
            value=endpoint_name,
            description="SageMaker endpoint name",
        )
        CfnOutput(
            self, "EndpointArn",
            value=f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{endpoint_name}",
            description="SageMaker endpoint ARN",
        )
        CfnOutput(
            self, "SageMakerRoleArn",
            value=sagemaker_role.role_arn,
            description="SageMaker execution role ARN",
        )
        if data_capture_bucket:
            CfnOutput(
                self, "DataCaptureBucketName",
                value=data_capture_bucket.bucket_name,
                description="S3 bucket for data capture",
            )
