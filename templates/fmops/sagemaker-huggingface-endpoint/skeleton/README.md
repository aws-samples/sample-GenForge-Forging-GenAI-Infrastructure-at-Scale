# ${{ values.name }} - SageMaker HuggingFace Endpoint

Deploy HuggingFace models on SageMaker with Text Generation Inference (TGI) container, provisioned by GenForge.

## Architecture

```
+----------------------------------------------------------------------+
|               SageMaker HuggingFace Endpoint                          |
|                                                                      |
|  +--------------------+    +--------------------+                    |
|  | HuggingFace Hub    |    | TGI Container      |                    |
|  | Model: ${{ values.huggingfaceModelId }}        |    | Version: ${{ values.tgiVersion }}          |                    |
|  +--------------------+    +--------------------+                    |
|           |                         |                                 |
|           v                         v                                 |
|  +--------------------------------------------+                      |
|  |         SageMaker Endpoint                   |                      |
|  |         Instance: ${{ values.instanceType }}                 |                      |
|  +--------------------------------------------+                      |
|                      |                                                |
|           +----------+----------+                                     |
|           |                     |                                     |
|           v                     v                                     |
|  +------------------+  +------------------+                           |
|  | Auto Scaling     |  | CloudWatch       |                           |
|  | (Target: 70 inv) |  | Alarms           |                           |
|  +------------------+  +------------------+                           |
+----------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| HuggingFace Model | ${{ values.huggingfaceModelId }} |
| Task Type | ${{ values.taskType }} |
| Instance Type | ${{ values.instanceType }} |
| TGI Version | ${{ values.tgiVersion }} |
| Quantization | ${{ values.quantization }} |

## Deployment

### Prerequisites

1. AWS account with OIDC provider configured for GitHub Actions
2. Sufficient service quota for the selected GPU instance type
3. For gated models (e.g., Llama), accept the license on HuggingFace Hub

### Deploy Infrastructure

Push to `main` branch or manually trigger the deploy workflow:

```bash
gh workflow run deploy.yml
```

### Destroy Infrastructure

```bash
gh workflow run destroy.yml -f confirm=destroy
```

## Usage

### Invoke the Endpoint

```python
import boto3
import json

runtime = boto3.client("sagemaker-runtime", region_name="${{ values.awsRegion }}")

response = runtime.invoke_endpoint(
    EndpointName="${{ values.name }}-${{ values.environment }}-endpoint",
    ContentType="application/json",
    Body=json.dumps({
        "inputs": "What is deep learning?",
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
            "top_p": 0.9,
        }
    }),
)

result = json.loads(response["Body"].read().decode())
print(result[0]["generated_text"])
```

### Auto Scaling

The endpoint scales between 1-4 instances based on InvocationsPerInstance:
- **Target**: 70 invocations per instance per minute
- **Scale-out cooldown**: 60 seconds
- **Scale-in cooldown**: 300 seconds

### Monitor

- **SageMaker Console**: Endpoint status, instance metrics
- **CloudWatch**: Latency, error rates, invocation counts

## Cost Estimation

Costs depend on:
- **Instance type**: ${{ values.instanceType }} (billed per hour while endpoint is running)
- **Auto scaling**: 1-4 instances based on traffic

Check [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) for current rates.

## Support

For issues, contact the ${{ values.owner }} team.
