#!/usr/bin/env python3
"""CDK app entry point for SageMaker JumpStart Endpoint."""

import os
import aws_cdk as cdk
from stack import SageMakerJumpStartEndpointStack

app = cdk.App()

env_config = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "${{ values.awsAccountId }}"),
    region=os.environ.get("CDK_DEFAULT_REGION", "${{ values.awsRegion }}"),
)

SageMakerJumpStartEndpointStack(
    app,
    "${{ values.name }}-${{ values.environment }}-stack",
    component_name="${{ values.name }}",
    jumpstart_model_id="${{ values.jumpstartModelId }}",
    instance_type="${{ values.instanceType }}",
    initial_instance_count=${{ values.initialInstanceCount }},
    enable_data_capture="${{ values.enableDataCapture }}" == "true",
    data_capture_percent=${{ values.dataCapturePercent }},
    environment="${{ values.environment }}",
    env=env_config,
)

app.synth()
