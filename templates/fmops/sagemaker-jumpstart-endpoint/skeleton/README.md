# ${{ values.name }} - SageMaker JumpStart Endpoint

Deploy pre-trained foundation models from SageMaker JumpStart as real-time inference endpoints, provisioned by GenForge.

## Architecture

```
+----------------------------------------------------------------------+
|                  SageMaker JumpStart Endpoint                         |
|                                                                      |
|  +--------------------+    +--------------------+                    |
|  | JumpStart Model    |--->| Endpoint Config    |                    |
|  | (Pre-trained)      |    | (Instance, Capture)|                    |
|  +--------------------+    +--------------------+                    |
|                                    |                                  |
|                                    v                                  |
|                           +------------------+                        |
|                           | SageMaker        |                        |
|                           | Endpoint         |                        |
|                           | (Real-time)      |                        |
|                           +------------------+                        |
|                                    |                                  |
|                      +-------------+-------------+                    |
|                      |                           |                    |
|                      v                           v                    |
|            +------------------+        +------------------+           |
|            | CloudWatch       |        | S3 Data Capture  |           |
|            | Alarms           |        | (Optional)       |           |
|            +------------------+        +------------------+           |
+----------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| Model ID | ${{ values.jumpstartModelId }} |
| Instance Type | ${{ values.instanceType }} |
| Instance Count | ${{ values.initialInstanceCount }} |
| Data Capture | ${{ values.enableDataCapture }} |

## Deployment

### Prerequisites

1. AWS account with OIDC provider configured for GitHub Actions
2. Sufficient service quota for the selected instance type

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
        "inputs": "What is machine learning?",
        "parameters": {"max_new_tokens": 256, "temperature": 0.7}
    }),
)

result = json.loads(response["Body"].read().decode())
print(result)
```

### Monitor

- **SageMaker Console**: Endpoint status, metrics, and logs
- **CloudWatch**: Latency, error rates, and invocation metrics

## Cost Estimation

Costs depend on:
- **Instance type**: ${{ values.instanceType }} (billed per hour while endpoint is running)
- **Instance count**: ${{ values.initialInstanceCount }}
- **Data capture**: S3 storage for captured data (if enabled)

Check [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) for current rates.

## Support

For issues, contact the ${{ values.owner }} team.
