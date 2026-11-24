#!/usr/bin/env python3
"""CDK app entry point for SageMaker HuggingFace Endpoint."""

import os
import aws_cdk as cdk
from stack import SageMakerHuggingFaceEndpointStack

app = cdk.App()

env_config = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "${{ values.awsAccountId }}"),
    region=os.environ.get("CDK_DEFAULT_REGION", "${{ values.awsRegion }}"),
)

SageMakerHuggingFaceEndpointStack(
    app,
    "${{ values.name }}-${{ values.environment }}-stack",
    component_name="${{ values.name }}",
    huggingface_model_id="${{ values.huggingfaceModelId }}",
    task_type="${{ values.taskType }}",
    instance_type="${{ values.instanceType }}",
    tgi_version="${{ values.tgiVersion }}",
    quantization="${{ values.quantization }}",
    environment="${{ values.environment }}",
    env=env_config,
)

app.synth()
