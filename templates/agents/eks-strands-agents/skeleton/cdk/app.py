#!/usr/bin/env python3
"""CDK app entry point for Strands AI Agent on EKS infrastructure."""

import aws_cdk as cdk
from stack import StrandsAgentStack

app = cdk.App()

# Configuration from CDK context (set by GitHub Actions) or scaffolder defaults
component_name = app.node.try_get_context("component_name") or "${{ values.name }}"
environment = app.node.try_get_context("environment") or "${{ values.environment }}"
eks_cluster_name = app.node.try_get_context("eks_cluster_name") or "${{ values.eksClusterName }}"
ecr_repo_name = app.node.try_get_context("ecr_repo_name") or "${{ values.ecrRepoName }}"
bedrock_model_id = app.node.try_get_context("bedrock_model_id") or "${{ values.bedrockModelId }}"

StrandsAgentStack(
    app,
    f"{component_name}-{environment}-stack",
    component_name=component_name,
    environment=environment,
    eks_cluster_name=eks_cluster_name,
    ecr_repo_name=ecr_repo_name,
    bedrock_model_id=bedrock_model_id,
    env=cdk.Environment(
        account=app.node.try_get_context("aws_account_id") or "${{ values.awsAccountId }}",
        region=app.node.try_get_context("aws_region") or "${{ values.awsRegion }}",
    ),
    tags={
        "environment": environment,
        "owner": "${{ values.owner }}",
        "genforge:managed": "true",
    },
)

app.synth()
