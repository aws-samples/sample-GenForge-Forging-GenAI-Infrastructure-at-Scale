#!/usr/bin/env python3
"""CDK app entry point for Bedrock Fine-Tuning pipeline."""

import os
import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks
from stack import BedrockFinetuningStack

app = cdk.App()

env_config = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "${{ values.awsAccountId }}"),
    region=os.environ.get("CDK_DEFAULT_REGION", "${{ values.awsRegion }}"),
)

BedrockFinetuningStack(
    app,
    "${{ values.name }}-${{ values.environment }}-stack",
    # Component info
    component_name="${{ values.name }}",
    # Model configuration
    base_model_id="${{ values.baseModelId }}",
    customization_type="${{ values.customizationType }}",
    # Training configuration
    training_epochs=${{ values.trainingEpochs }},
    batch_size=${{ values.batchSize }},
    learning_rate=${{ values.learningRate }},
    warmup_ratio=${{ values.warmupRatio }},
    # Data configuration
    enable_data_validation="${{ values.enableDataValidation }}" == "true",
    max_training_data_size_mb=${{ values.maxTrainingDataSizeMb }},
    validation_data_ratio=${{ values.validationDataRatio }},
    # Output configuration
    enable_provisioned_throughput="${{ values.enableProvisionedThroughput }}" == "true",
    provisioned_model_units=${{ values.provisionedModelUnits }},
    # Notifications
    enable_notifications="${{ values.enableNotifications }}" == "true",
    notification_email="${{ values.notificationEmail }}" or None,
    # Environment
    environment="${{ values.environment }}",
    env=env_config,
)

# Apply cdk-nag security checks - emits findings to cdk.out/AwsSolutions-*.csv
# Set CDK_NAG_DISABLE=1 to skip (e.g., for local dev or the deploy job
# after security-scan has already run).
if os.environ.get("CDK_NAG_DISABLE") != "1":
    cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

app.synth()
