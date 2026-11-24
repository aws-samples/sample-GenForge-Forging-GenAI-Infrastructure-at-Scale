"""Strands AI Agent on EKS - CDK Stack.

This stack provisions the AWS resources needed to run Strands AI agents
on an existing EKS cluster with Amazon Bedrock as the LLM backend.

Resources created:
- ECR Repository for agent container images
- IAM Role for EKS pod identity (IRSA) with Bedrock and CloudWatch permissions
- CloudWatch Log Group for agent logs

The EKS cluster must already exist. After CDK deploy, use the generated
Helm chart values and Kubernetes manifests to deploy the agent workload.
"""

from typing import Any
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    RemovalPolicy,
)
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct


class StrandsAgentStack(Stack):
    """CDK stack for Strands AI Agent infrastructure on EKS."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        environment: str,
        eks_cluster_name: str,
        ecr_repo_name: str,
        bedrock_model_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal_policy = (
            RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # -------------------------------------------------------------------
        # ECR Repository
        # -------------------------------------------------------------------
        ecr_repository = ecr.Repository(
            self,
            "AgentEcrRepository",
            repository_name=f"{component_name}-{environment}-{ecr_repo_name}",
            removal_policy=removal_policy,
            image_scan_on_push=True,
            encryption=ecr.RepositoryEncryption.AES_256,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Remove untagged images after 7 days",
                    tag_status=ecr.TagStatus.UNTAGGED,
                    max_image_age=cdk.Duration.days(7),
                ),
                ecr.LifecycleRule(
                    description="Keep at most 25 tagged images",
                    tag_status=ecr.TagStatus.TAGGED,
                    tag_prefix_list=["v"],
                    max_image_count=25,
                ),
            ],
        )

        # -------------------------------------------------------------------
        # CloudWatch Log Group
        # -------------------------------------------------------------------
        log_group = logs.LogGroup(
            self,
            "AgentLogGroup",
            log_group_name=f"/genforge/{component_name}-{environment}/strands-agent",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
        )

        # -------------------------------------------------------------------
        # IAM Role for EKS Pod Identity (IRSA)
        # -------------------------------------------------------------------
        # The trust policy assumes EKS OIDC provider will be configured.
        # The exact OIDC provider URL is cluster-specific and must be
        # substituted after deployment via the Helm chart values.
        agent_role = iam.Role(
            self,
            "AgentPodRole",
            role_name=f"{component_name}-{environment}-agent-role",
            description=f"IAM role for Strands agent pods in EKS cluster {eks_cluster_name}",
            assumed_by=iam.CompositePrincipal(
                # Federated principal placeholder for IRSA
                # After deploy, update trust policy with actual EKS OIDC provider
                iam.FederatedPrincipal(
                    federated=f"arn:aws:iam::{self.account}:oidc-provider/oidc.eks.{self.region}.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE",
                    conditions={
                        "StringEquals": {
                            f"oidc.eks.{self.region}.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": f"system:serviceaccount:{component_name}:{component_name}-sa",
                            f"oidc.eks.{self.region}.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com",
                        }
                    },
                    assume_role_action="sts:AssumeRoleWithWebIdentity",
                ),
            ),
            max_session_duration=cdk.Duration.hours(4),
        )

        # Bedrock permissions for agent LLM calls
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeModel",
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/{bedrock_model_id}",
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/*",
                ],
            )
        )

        # CloudWatch Logs permissions for agent observability
        agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    log_group.log_group_arn,
                    f"{log_group.log_group_arn}:*",
                ],
            )
        )

        # -------------------------------------------------------------------
        # Tags
        # -------------------------------------------------------------------
        Tags.of(self).add("Name", f"{component_name}-{environment}-strands-agent")
        Tags.of(self).add("environment", environment)
        Tags.of(self).add("owner", kwargs.get("tags", {}).get("owner", "platform-team"))
        Tags.of(self).add("genforge:managed", "true")
        Tags.of(self).add("eks-cluster", eks_cluster_name)

        # -------------------------------------------------------------------
        # Outputs
        # -------------------------------------------------------------------
        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=ecr_repository.repository_uri,
            description="ECR repository URI for agent container images",
            export_name=f"{construct_id}-ecr-repo-uri",
        )

        CfnOutput(
            self,
            "AgentRoleArn",
            value=agent_role.role_arn,
            description="IAM role ARN for EKS pod identity (IRSA)",
            export_name=f"{construct_id}-agent-role-arn",
        )

        CfnOutput(
            self,
            "ServiceAccountName",
            value=f"{component_name}-sa",
            description="Kubernetes ServiceAccount name for the agent pods",
            export_name=f"{construct_id}-service-account-name",
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=log_group.log_group_name,
            description="CloudWatch Log Group for agent logs",
            export_name=f"{construct_id}-log-group-name",
        )

        CfnOutput(
            self,
            "EksClusterName",
            value=eks_cluster_name,
            description="Target EKS cluster name",
            export_name=f"{construct_id}-eks-cluster-name",
        )

        CfnOutput(
            self,
            "BedrockModelId",
            value=bedrock_model_id,
            description="Bedrock model ID configured for this agent",
            export_name=f"{construct_id}-bedrock-model-id",
        )

        CfnOutput(
            self,
            "HelmValuesSnippet",
            value=(
                f"serviceAccount.name={component_name}-sa,"
                f"serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn={agent_role.role_arn},"
                f"image.repository={ecr_repository.repository_uri},"
                f"env.BEDROCK_MODEL_ID={bedrock_model_id},"
                f"env.AWS_REGION={self.region},"
                f"env.LOG_GROUP_NAME={log_group.log_group_name}"
            ),
            description="Helm --set values snippet for deploying the agent chart",
            export_name=f"{construct_id}-helm-values",
        )
