#!/usr/bin/env python3
"""CDK app entry point for MLflow AI Gateway on ECS Fargate."""

import aws_cdk as cdk
from stack import MlflowAiGatewayStack

app = cdk.App()

# Configuration from CDK context (set by GitHub Actions) or scaffolder defaults
component_name = app.node.try_get_context("component_name") or "${{ values.name }}"
environment = app.node.try_get_context("environment") or "${{ values.environment }}"
vpc_id = app.node.try_get_context("vpc_id") or "${{ values.vpcId }}"
private_subnet_ids = app.node.try_get_context("private_subnet_ids") or "${{ values.privateSubnetIds }}"
public_subnet_ids = app.node.try_get_context("public_subnet_ids") or "${{ values.publicSubnetIds }}"
certificate_arn = app.node.try_get_context("certificate_arn") or "${{ values.certificateArn }}"
backend_store_type = app.node.try_get_context("backend_store_type") or "${{ values.backendStoreType }}"
artifact_bucket_name = app.node.try_get_context("artifact_bucket_name") or "${{ values.artifactBucketName }}"
container_cpu = int(app.node.try_get_context("container_cpu") or "${{ values.containerCpu }}")
container_memory = int(app.node.try_get_context("container_memory") or "${{ values.containerMemory }}")
desired_count = int(app.node.try_get_context("desired_count") or "${{ values.desiredCount }}")
enable_auto_scaling = str(app.node.try_get_context("enable_auto_scaling") or "${{ values.enableAutoScaling }}").lower() == "true"

MlflowAiGatewayStack(
    app,
    f"{component_name}-{environment}-stack",
    component_name=component_name,
    environment=environment,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    public_subnet_ids=public_subnet_ids,
    certificate_arn=certificate_arn,
    backend_store_type=backend_store_type,
    artifact_bucket_name=artifact_bucket_name,
    container_cpu=container_cpu,
    container_memory=container_memory,
    desired_count=desired_count,
    enable_auto_scaling=enable_auto_scaling,
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
