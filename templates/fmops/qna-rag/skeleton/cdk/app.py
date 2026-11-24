#!/usr/bin/env python3
"""CDK app entry point for QnA RAG Pipeline."""

import os
import aws_cdk as cdk
from stack import QnARagStack

app = cdk.App()

env_config = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "${{ values.awsAccountId }}"),
    region=os.environ.get("CDK_DEFAULT_REGION", "${{ values.awsRegion }}"),
)

private_subnet_ids = [
    s.strip() for s in "${{ values.privateSubnetIds }}".split(",") if s.strip()
]

QnARagStack(
    app,
    "${{ values.name }}-${{ values.environment }}-stack",
    component_name="${{ values.name }}",
    vpc_id="${{ values.vpcId }}",
    private_subnet_ids=private_subnet_ids,
    bedrock_model_id="${{ values.bedrockModelId }}",
    embedding_model_id="${{ values.embeddingModelId }}",
    collection_name="${{ values.collectionName }}" or "${{ values.name }}-vectors",
    vector_index_name="${{ values.vectorIndexName }}",
    vector_dimensions=${{ values.vectorDimensions }},
    environment="${{ values.environment }}",
    opensearch_vpc_endpoint_id="${{ values.opensearchVpcEndpointId }}",
    env=env_config,
)

app.synth()
