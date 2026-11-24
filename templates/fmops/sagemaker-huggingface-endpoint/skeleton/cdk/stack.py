"""SageMaker HuggingFace Endpoint CDK Stack.

This stack provisions:
- IAM role for SageMaker with necessary permissions
- SageMaker Model with HuggingFace DLC image URI (TGI container)
- Environment variables: HF_MODEL_ID, HF_TASK, QUANTIZE
- SageMaker EndpointConfig
- SageMaker Endpoint
- Application Auto Scaling (target tracking on InvocationsPerInstance, target 70)
- CloudWatch alarms for latency and error monitoring
"""

from typing import Any
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    RemovalPolicy,
)
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct


# HuggingFace TGI Deep Learning Container registry per region
# These are the AWS DLC account IDs for HuggingFace TGI images
TGI_DLC_ACCOUNTS = {
    "us-east-1": "763104351884",
    "us-west-2": "763104351884",
    "eu-west-1": "763104351884",
}

# TGI version to image tag mapping
TGI_IMAGE_TAGS = {
    "2.3.1": "2.3.1-tgi2.3.1-gpu-py311-cu124-ubuntu22.04",
    "2.2.0": "2.2.0-tgi2.2.0-gpu-py311-cu121-ubuntu22.04",
    "2.0.1": "2.0.1-tgi2.0.1-gpu-py310-cu121-ubuntu22.04",
}


class SageMakerHuggingFaceEndpointStack(Stack):
    """SageMaker HuggingFace Model Endpoint with TGI container."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        huggingface_model_id: str,
        task_type: str = "text-generation",
        instance_type: str = "ml.g5.xlarge",
        tgi_version: str = "2.3.1",
        quantization: str = "none",
        environment: str = "dev",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        endpoint_name = f"{component_name}-{environment}-endpoint"

        # ------------------------------------------------------------------ #
        # KMS Key
        # ------------------------------------------------------------------ #
        encryption_key = kms.Key(
            self,
            "EncryptionKey",
            alias=f"{component_name}-{environment}-hf-key",
            enable_key_rotation=True,
            removal_policy=removal,
            description=f"Encryption key for {component_name} HuggingFace endpoint",
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
                f"HuggingFace endpoint - no managed policies attached."
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

        # HuggingFace DLC image pull.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImagePull",
                actions=[
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=[
                    f"arn:aws:ecr:{self.region}:763104351884:repository/huggingface-pytorch-tgi-inference",
                ],
            )
        )

        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRAuthToken",
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],  # This API action does not support resource-level permissions.
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
        # Build container image URI
        # ------------------------------------------------------------------ #
        dlc_account = TGI_DLC_ACCOUNTS.get(self.region, "763104351884")
        image_tag = TGI_IMAGE_TAGS.get(tgi_version, TGI_IMAGE_TAGS["2.3.1"])
        image_uri = (
            f"{dlc_account}.dkr.ecr.{self.region}.amazonaws.com/"
            f"huggingface-pytorch-tgi-inference:{image_tag}"
        )

        # ------------------------------------------------------------------ #
        # Container environment variables
        # ------------------------------------------------------------------ #
        container_env = {
            "HF_MODEL_ID": huggingface_model_id,
            "HF_TASK": task_type,
            "MAX_INPUT_LENGTH": "2048",
            "MAX_TOTAL_TOKENS": "4096",
        }

        if quantization != "none":
            container_env["QUANTIZE"] = quantization

        # ------------------------------------------------------------------ #
        # SageMaker Model
        # ------------------------------------------------------------------ #
        model = sagemaker.CfnModel(
            self,
            "HuggingFaceModel",
            model_name=f"{component_name}-{environment}-model",
            execution_role_arn=sagemaker_role.role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=image_uri,
                environment=container_env,
            ),
        )

        # ------------------------------------------------------------------ #
        # SageMaker EndpointConfig
        # ------------------------------------------------------------------ #
        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "EndpointConfig",
            endpoint_config_name=f"{component_name}-{environment}-config",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    model_name=model.model_name or f"{component_name}-{environment}-model",
                    instance_type=instance_type,
                    initial_instance_count=1,
                    initial_variant_weight=1.0,
                ),
            ],
            kms_key_id=encryption_key.key_id,
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
        # Application Auto Scaling
        # ------------------------------------------------------------------ #
        scaling_target = appscaling.ScalableTarget(
            self,
            "ScalingTarget",
            service_namespace=appscaling.ServiceNamespace.SAGEMAKER,
            resource_id=f"endpoint/{endpoint_name}/variant/AllTraffic",
            scalable_dimension="sagemaker:variant:DesiredInstanceCount",
            min_capacity=1,
            max_capacity=4,
        )
        scaling_target.node.add_dependency(endpoint)

        scaling_target.scale_to_track_metric(
            "InvocationScaling",
            target_value=70,
            custom_metric=cloudwatch.Metric(
                namespace="AWS/SageMaker",
                metric_name="InvocationsPerInstance",
                dimensions_map={
                    "EndpointName": endpoint_name,
                    "VariantName": "AllTraffic",
                },
                statistic="Sum",
                period=cdk.Duration.minutes(1),
            ),
            scale_in_cooldown=cdk.Duration.seconds(300),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

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
            self, "ModelId",
            value=huggingface_model_id,
            description="HuggingFace model ID",
        )
        CfnOutput(
            self, "ContainerImage",
            value=image_uri,
            description="TGI container image URI",
        )
        CfnOutput(
            self, "SageMakerRoleArn",
            value=sagemaker_role.role_arn,
            description="SageMaker execution role ARN",
        )
