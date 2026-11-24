# ${{ values.name }} - SageMaker LLM Fine-Tuning

Fine-tune large language models with LoRA (Low-Rank Adaptation) on SageMaker, provisioned by GenForge.

## Architecture

```
+----------------------------------------------------------------------+
|                  SageMaker LLM Fine-Tuning Pipeline                   |
|                                                                      |
|  +-------------------+                                               |
|  | S3 Bucket         |                                               |
|  | - training-data/  |                                               |
|  | - model-artifacts/|                                               |
|  +-------------------+                                               |
|           |                                                           |
|           v                                                           |
|  +-------------------------------------------+                       |
|  |         Step Functions Workflow            |                       |
|  |                                           |                       |
|  |  +--------------+    +----------------+   |                       |
|  |  | Start        |--->| Poll Status    |   |                       |
|  |  | Training Job |    | (every 5 min)  |   |                       |
|  |  +--------------+    +----------------+   |                       |
|  |                            |              |                       |
|  |                     +------+------+       |                       |
|  |                     |             |       |                       |
|  |                  Success       Failed     |                       |
|  +-------------------------------------------+                       |
|                      |                                                |
|                      v                                                |
|  +-------------------------------------------+                       |
|  |        SageMaker Training Job              |                       |
|  |  Model: ${{ values.baseModel }}                              |                       |
|  |  Instance: ${{ values.instanceType }} x ${{ values.instanceCount }}                  |                       |
|  |  LoRA Rank: ${{ values.loraRank }}                                  |                       |
|  +-------------------------------------------+                       |
+----------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| Base Model | ${{ values.baseModel }} |
| Instance Type | ${{ values.instanceType }} |
| Instance Count | ${{ values.instanceCount }} |
| Epochs | ${{ values.epochs }} |
| LoRA Rank | ${{ values.loraRank }} |
| Learning Rate | ${{ values.learningRate }} |
| Validation Split | ${{ values.validationSplit }} |

## Deployment

### Prerequisites

1. AWS account with OIDC provider configured for GitHub Actions
2. Sufficient service quota for the selected GPU instance type
3. For gated models (e.g., Llama), configure HuggingFace token

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

### 1. Prepare Training Data

Format your training data as JSONL with instruction-response pairs:

```json
{"instruction": "Summarize the following text", "input": "Long document text...", "output": "Summary here"}
{"instruction": "Translate to French", "input": "Hello world", "output": "Bonjour le monde"}
```

### 2. Upload Training Data

```bash
aws s3 cp training_data.jsonl \
  s3://${{ values.name }}-${{ values.environment }}-data-${{ values.awsAccountId }}/training-data/
```

### 3. Start Fine-Tuning

Start an execution of the Step Functions state machine:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:${{ values.awsRegion }}:${{ values.awsAccountId }}:stateMachine:${{ values.name }}-${{ values.environment }}-training-workflow \
  --input '{"jobName": "my-finetune-job"}'
```

### 4. Monitor Training

- **Step Functions Console**: View workflow execution and status
- **SageMaker Console**: Training job details, metrics, and logs
- **CloudWatch**: Detailed training metrics (loss, learning rate)

### 5. Use the Fine-Tuned Model

After training completes, model artifacts are saved to:
`s3://${{ values.name }}-${{ values.environment }}-data-${{ values.awsAccountId }}/model-artifacts/<job-name>/`

Deploy the model to a SageMaker endpoint or merge LoRA weights for inference.

## LoRA Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| LoRA Rank | ${{ values.loraRank }} | Rank of low-rank matrices (higher = more parameters) |
| LoRA Alpha | Auto (2x rank) | Scaling factor for LoRA updates |
| LoRA Dropout | 0.05 | Dropout rate for regularization |
| FP16 | Enabled | Mixed precision training |

## Cost Estimation

Costs depend on:
- **Instance type**: ${{ values.instanceType }} x ${{ values.instanceCount }} instances
- **Training duration**: Depends on data size and epochs
- **Storage**: S3 storage for data and model artifacts

Check [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/) for current rates.

## Support

For issues, contact the ${{ values.owner }} team.
