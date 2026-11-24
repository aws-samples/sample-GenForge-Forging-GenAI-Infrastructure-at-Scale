# ${{ values.name }} - Bedrock Fine-Tuning Pipeline

Fine-tune Amazon Bedrock foundation models with automated pipelines provisioned by GenForge.

## Architecture

```
+----------------------------------------------------------------------+
|                    Bedrock Fine-Tuning Pipeline                       |
|                                                                      |
|  +------------+   +------------+   +------------+   +------------+   |
|  |  Upload    |-->|  Validate  |-->|  Fine-Tune |-->|  Deploy    |   |
|  |  Data      |   |  Data      |   |  Model     |   |  Model     |   |
|  +------------+   +------------+   +------------+   +------------+   |
|       |                |                |                |           |
|       v                v                v                v           |
|  +------------+   +------------+   +------------+   +------------+   |
|  | S3 Bucket  |   |  Lambda    |   |  Bedrock   |   | Provisioned|   |
|  | (Training) |   | (Validate) |   | Custom Job |   |   Model    |   |
|  +------------+   +------------+   +------------+   +------------+   |
|                                                                      |
|                  +-------------------------+                         |
|                  |    Step Functions       |                         |
|                  |   (Orchestration)       |                         |
|                  +-------------------------+                         |
|                            |                                         |
|                            v                                         |
|                  +-------------------------+                         |
|                  |    SNS (Notify)         |                         |
|                  +-------------------------+                         |
+----------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| Base Model | ${{ values.baseModelId }} |
| Customization Type | ${{ values.customizationType }} |
| Training Epochs | ${{ values.trainingEpochs }} |
| Batch Size | ${{ values.batchSize }} |
| Learning Rate | ${{ values.learningRate }} |
| Data Validation | ${{ values.enableDataValidation }} |

## Deployment

### Prerequisites

1. AWS account with OIDC provider configured for GitHub Actions
2. Bedrock model access granted in the AWS console
3. GitHub repository secrets configured

### Deploy Infrastructure

Push to `main` branch or manually trigger the deploy workflow:

```bash
gh workflow run deploy.yml
```

### Destroy Infrastructure

Manually trigger the destroy workflow with confirmation:

```bash
gh workflow run destroy.yml -f confirm=destroy
```

## Usage

### 1. Prepare Training Data

Format your training data as JSONL:

**For Fine-Tuning:**
```json
{"prompt": "Your input text", "completion": "Expected output"}
```

**For Continued Pre-Training:**
```json
{"input": "Your training document text..."}
```

### 2. Upload Training Data

```bash
aws s3 cp training_data.jsonl \
  s3://${{ values.name }}-${{ values.environment }}-training-data-${{ values.awsAccountId }}/training/
```

### 3. Start Fine-Tuning Job

Start an execution of the Step Functions state machine:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:${{ values.awsRegion }}:${{ values.awsAccountId }}:stateMachine:${{ values.name }}-${{ values.environment }}-finetuning-workflow \
  --input '{"jobName": "my-job", "trainingDataS3Uri": "s3://..."}'
```

### 4. Monitor Progress

- **Step Functions Console**: View execution status and logs
- **Bedrock Console**: Monitor customization job progress
- **CloudWatch**: View detailed metrics and logs
{% if values.enableNotifications %}- **Email**: Receive status notifications at ${{ values.notificationEmail }}{% endif %}

## Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Epochs | ${{ values.trainingEpochs }} | Number of training passes |
| Batch Size | ${{ values.batchSize }} | Samples per training step |
| Learning Rate | ${{ values.learningRate }} | Step size for optimization |
| Warmup Ratio | ${{ values.warmupRatio }} | Fraction of warmup steps |

## Cost Estimation

Bedrock fine-tuning costs depend on:
- **Training**: Token count x epochs x model rate
- **Storage**: Model artifacts in S3
- **Provisioned Throughput**: If enabled (${{ values.enableProvisionedThroughput }})

Check [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.

## Support

For issues, contact the ${{ values.owner }} team.
