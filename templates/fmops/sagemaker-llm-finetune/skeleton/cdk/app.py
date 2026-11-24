#!/usr/bin/env python3
"""CDK app entry point for SageMaker LLM Fine-Tuning."""

import os
import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from stack import SageMakerLLMFineTuneStack

app = cdk.App()

env_config = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "${{ values.awsAccountId }}"),
    region=os.environ.get("CDK_DEFAULT_REGION", "${{ values.awsRegion }}"),
)

stack = SageMakerLLMFineTuneStack(
    app,
    "${{ values.name }}-${{ values.environment }}-stack",
    component_name="${{ values.name }}",
    base_model="${{ values.baseModel }}",
    instance_type="${{ values.instanceType }}",
    instance_count=${{ values.instanceCount }},
    epochs=${{ values.epochs }},
    lora_rank=${{ values.loraRank }},
    learning_rate=${{ values.learningRate }},
    training_data_s3_path="${{ values.trainingDataS3Path }}" or None,
    validation_split=${{ values.validationSplit }},
    environment="${{ values.environment }}",
    env=env_config,
)

# Apply cdk-nag security checks - emits findings to cdk.out/AwsSolutions-*.csv
# Set CDK_NAG_DISABLE=1 to skip (e.g., for local dev)
if os.environ.get("CDK_NAG_DISABLE") != "1":
    cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
