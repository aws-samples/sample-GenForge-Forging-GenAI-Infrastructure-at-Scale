# ${{ values.name }} - MLflow AI Gateway

MLflow AI Gateway on ECS Fargate with experiment tracking, artifact storage, and Bedrock integration.

## Architecture

```
+-------------------------------------------------------------------------+
|                      MLflow AI Gateway on Fargate                       |
|                                                                         |
|  +--------------------+                                                 |
|  | Application Load   |                                                 |
|  | Balancer           |                                                 |
|  | HTTPS:443 (ACM)    |                                                 |
|  | HTTP:80 -> 443     |                                                 |
|  +--------+-----------+                                                 |
|           |                                                             |
|  +--------v-----------+     +-------------------+     +--------------+  |
|  | ECS Fargate        |     |   S3 Bucket       |     |  DynamoDB    |  |
|  | Cluster            |---->|   (Artifacts)     |     |  (Tracking)  |  |
|  |                    |     |   SSE-KMS         |     |  PAY_PER_REQ |  |
|  | +----------------+ |     +-------------------+     +--------------+  |
|  | | MLflow         | |                                                 |
|  | | Container      | |     +-------------------+     +--------------+  |
|  | | (Gunicorn)     | |---->|  Amazon Bedrock   |     |  CloudWatch  |  |
|  | +----------------+ |     |  (LLM Backend)    |     |  (Logs)      |  |
|  |                    |     +-------------------+     +--------------+  |
|  | +----------------+ |                                                 |
|  | | Auto Scaling   | |     +-------------------+                       |
|  | | (CPU 70%)      | |     |  ECR Repository   |                       |
|  | +----------------+ |     |  (MLflow Image)   |                       |
|  +--------------------+     +-------------------+                       |
+-------------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| VPC ID | ${{ values.vpcId }} |
| Container CPU | ${{ values.containerCpu }} units |
| Container Memory | ${{ values.containerMemory }} MiB |
| Desired Count | ${{ values.desiredCount }} |
| Auto Scaling | ${{ values.enableAutoScaling }} |
| Backend Store | ${{ values.backendStoreType }} |

## Prerequisites

Before deploying this template, ensure the following are in place:

1. **AWS CDK Bootstrap** -- Bootstrap your AWS account for CDK deployments (one-time setup per account/region):
   ```bash
   export AWS_REGION=${{ values.awsRegion }}
   export AWS_ACCOUNT_ID=${{ values.awsAccountId }}
   
   # Install pinned CDK version (matches the workflow pin, requires bootstrap v30+)
   npm install -g aws-cdk@2.170.0
   
   # Bootstrap (or re-bootstrap if you have an older version)
   cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION} --force
   ```
   
   **IMPORTANT**: Use `--force` flag to upgrade from older CDK bootstrap versions (e.g., version 25 to 30+). Without this, deployments will fail with "Bootstrap toolkit stack version 30 or later is needed".

2. **GitHub OIDC Provider** -- Configure GitHub Actions OIDC authentication (one-time setup per organization):
   
   Use the setup script from the EKS Strands Agents template:
   ```bash
   # If you've already deployed the EKS Strands Agents template, the OIDC setup is done
   # Otherwise, get the script from: templates/agents/eks-strands-agents/skeleton/scripts/setup-github-oidc.sh
   
   ./setup-github-oidc.sh <your-github-org>
   ```
   
   This creates:
   - GitHub OIDC provider for `token.actions.githubusercontent.com`
   - IAM role `GitHubActionsDeployRole` with trust policy for your GitHub organization
   - Required permissions: ECR, ECS, S3, DynamoDB, CloudFormation, IAM, CloudWatch

3. **VPC** -- An existing VPC with public and private subnets (use the GenForge VPC template if needed)
   - Public subnets for the Application Load Balancer
   - Private subnets for ECS Fargate tasks

4. **Bedrock Access** -- Model access granted in the Bedrock console for desired models (optional, for AI Gateway routes)

## Deployment

### Deploy Infrastructure

Push to `main` branch or trigger the deploy workflow manually:

```bash
gh workflow run deploy.yml
```

This creates:
- ECR repository for MLflow container image
- S3 bucket for ML artifact storage (SSE-KMS encrypted)
- DynamoDB table for experiment tracking
- ECS Fargate cluster and service
- Application Load Balancer with health checks
- Auto scaling policy (if enabled)
- CloudWatch log group

### Access MLflow UI

After deployment, the MLflow UI is accessible via the ALB DNS name:

```bash
# Get the ALB DNS from CDK outputs
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name ${{ values.name }}-${{ values.environment }}-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text)

echo "MLflow UI: https://${ALB_DNS}"
```

### Destroy Infrastructure

Manually trigger the destroy workflow with confirmation:

```bash
gh workflow run destroy.yml -f confirm=destroy
```

## Usage

### Experiment Tracking

```python
import mlflow

# Set the tracking URI to the ALB endpoint (HTTPS with ACM cert)
mlflow.set_tracking_uri("https://<ALB_DNS_NAME>")

# Create or set an experiment
mlflow.set_experiment("my-genai-experiment")

# Log a run
with mlflow.start_run():
    mlflow.log_param("model", "claude-3-sonnet")
    mlflow.log_param("temperature", 0.7)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("latency_ms", 250)
    mlflow.log_artifact("output.json")
```

### AI Gateway Routes

Configure MLflow AI Gateway routes for unified LLM access:

```python
from mlflow.gateway import set_gateway_uri, query

set_gateway_uri("https://<ALB_DNS_NAME>")

response = query(
    route="bedrock-claude",
    data={
        "prompt": "Explain machine learning in simple terms.",
        "temperature": 0.7,
        "max_tokens": 500,
    },
)
print(response)
```

### Model Registry

```python
import mlflow

mlflow.set_tracking_uri("https://<ALB_DNS_NAME>")

# Register a model
model_uri = "runs:/<run_id>/model"
mlflow.register_model(model_uri, "my-genai-model")

# Load a registered model
model = mlflow.pyfunc.load_model("models:/my-genai-model/Production")
```

## Infrastructure Details

### S3 Artifact Bucket

- **Name**: `${{ values.name }}-${{ values.environment }}-artifacts-${{ values.awsAccountId }}`
- **Encryption**: SSE-KMS (AWS managed key)
- **Versioning**: Enabled
- **Lifecycle**: Objects transition to Infrequent Access after 90 days

### DynamoDB Tracking Table

- **Name**: `${{ values.name }}-${{ values.environment }}-tracking`
- **Billing**: PAY_PER_REQUEST (on-demand)
- **Point-in-Time Recovery**: Enabled
- **Indexes**: Global secondary index on `status` + `start_time`

### ECS Fargate Service

- **CPU**: ${{ values.containerCpu }} units
- **Memory**: ${{ values.containerMemory }} MiB
- **Tasks**: ${{ values.desiredCount }} desired (auto-scales up to ${{ values.desiredCount }}x3)
- **Deployment**: Circuit breaker with rollback enabled
- **Health check**: `GET /health` on port 5000

## Monitoring

- **CloudWatch Logs**: `/genforge/${{ values.name }}-${{ values.environment }}/mlflow-gateway`
- **ECS Console**: Task status, deployments, and service events
- **ALB Metrics**: Request count, latency, HTTP error rates
- **Container Insights**: CPU and memory utilization per task

```bash
# View recent logs
aws logs tail /genforge/${{ values.name }}-${{ values.environment }}/mlflow-gateway --follow

# Check ECS service status
aws ecs describe-services \
  --cluster ${{ values.name }}-${{ values.environment }}-cluster \
  --services ${{ values.name }}-${{ values.environment }}-svc
```

## Troubleshooting

### Common Issues

1. **ECS Deployment Circuit Breaker Triggered**
   - This occurs when ECS tasks fail health checks repeatedly
   - Most common cause: No Docker image in ECR on first deployment
   - Solution: The workflow now creates ECR and builds the image BEFORE deploying ECS
   - If you still see this, check CloudWatch logs for container startup errors:
     ```bash
     aws logs tail /genforge/${{ values.name }}-${{ values.environment }}/mlflow-gateway --follow
     ```

2. **503 Service Unavailable**
   - ECS tasks may still be starting; wait for health check to pass (can take 60-90 seconds)
   - Check ECS service events: `aws ecs describe-services ...`
   - Verify target group health in the EC2 console

3. **Container Fails to Start**
   - Check CloudWatch logs for error messages
   - Verify ECR image exists and is tagged `latest`
   - Ensure task execution role can pull from ECR

4. **DynamoDB Access Denied**
   - Check task role has `dynamodb:*` permissions on the tracking table
   - Verify the table name matches the `MLFLOW_BACKEND_STORE_URI` env var

5. **S3 Permission Errors**
   - Check task role has S3 read/write on the artifact bucket
   - Verify bucket policy does not block ECS task role

6. **Auto Scaling Not Working**
   - Confirm auto scaling is enabled (`${{ values.enableAutoScaling }}`)
   - Check CloudWatch alarms for the CPU scaling policy
   - Verify min/max capacity is configured correctly

## Cost Estimation

| Resource | Estimated Monthly Cost (dev) |
|----------|------------------------------|
| ECS Fargate (2 tasks, 0.5 vCPU, 1 GB) | ~$30 |
| Application Load Balancer | ~$20 |
| S3 (artifact storage) | ~$1-5 (varies with usage) |
| DynamoDB (on-demand) | ~$1-5 (varies with usage) |
| CloudWatch Logs | ~$1-3 |
| **Total** | **~$53-63/month** |

## Support

For issues, contact the ${{ values.owner }} team.
