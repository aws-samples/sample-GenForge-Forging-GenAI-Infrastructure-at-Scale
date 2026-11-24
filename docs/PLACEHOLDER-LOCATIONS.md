# Placeholder Locations

This document lists all locations in the GenForge project that contain placeholders requiring substitution before production use. Placeholders are organized by category: manual configuration, catalog entities, and auto-substituted template values.

---

## 1. Root Configuration (Manual -- Required Before Running)

These environment variables must be set for Backstage to function correctly.

### app-config.yaml

| File | Placeholder | Description | When Needed |
|------|------------|-------------|-------------|
| `app-config.yaml` | `${GITHUB_TOKEN}` | GitHub Personal Access Token for Backstage GitHub integration (repo creation, catalog imports) | Always (dev and prod) |

### app-config.production.yaml

| File | Placeholder | Description | When Needed |
|------|------------|-------------|-------------|
| `app-config.production.yaml` | `${POSTGRES_HOST}` | PostgreSQL database host | Production only |
| `app-config.production.yaml` | `${POSTGRES_PORT}` | PostgreSQL database port (e.g., `5432`) | Production only |
| `app-config.production.yaml` | `${POSTGRES_USER}` | PostgreSQL database username | Production only |
| `app-config.production.yaml` | `${POSTGRES_PASSWORD}` | PostgreSQL database password | Production only |
| `app-config.production.yaml` | `${GITHUB_CLIENT_ID}` | GitHub OAuth App Client ID for user authentication | Production only |
| `app-config.production.yaml` | `${GITHUB_CLIENT_SECRET}` | GitHub OAuth App Client Secret for user authentication | Production only |

### app-config.local.yaml

This file is empty by default and is intended for local development overrides. No placeholders are present, but you can add local-only configuration here (it is gitignored in most setups).

---

## 2. AWS Account IDs (Manual -- Required Before First Use)

The catalog file `catalog/aws-accounts.yaml` contains placeholder AWS account IDs that must be replaced with your real account IDs. These accounts appear in the Scaffolder UI as selectable targets when users create new components.

| File | Placeholder | Current Title | Action |
|------|------------|---------------|--------|
| `catalog/aws-accounts.yaml` | `111111111111` | AWS Development Account | Replace with your real dev account ID |
| `catalog/aws-accounts.yaml` | `222222222222` | AWS Staging Account | Replace with your real staging account ID |
| `catalog/aws-accounts.yaml` | `333333333333` | AWS Production Account | Replace with your real production account ID |

You may also add additional accounts by duplicating the Resource YAML block and specifying a new account ID, title, description, and tags.

---

## 3. Organization Entities (Manual -- Customize for Your Org)

The catalog file `catalog/org.yaml` defines default teams and users. Update these to match your organization:

| File | Entity | Current Value | Action |
|------|--------|---------------|--------|
| `catalog/org.yaml` | Group | `platform-team` | Rename or keep as your platform engineering team |
| `catalog/org.yaml` | Group | `data-science-team` | Rename to match your data science team |
| `catalog/org.yaml` | Group | `data-engineering-team` | Rename to match your data engineering team |
| `catalog/org.yaml` | Group | `devops-team` | Rename to match your DevOps team |
| `catalog/org.yaml` | User | `guest` (member of `data-science-team`) | Replace with real users or configure SSO |

---

## 4. Scaffolder Email (Manual -- Optional)

| File | Placeholder | Current Value | Description |
|------|------------|---------------|-------------|
| `app-config.yaml` | `scaffolder.defaultAuthor.email` | `genforge@example.com` | Email used as the commit author for scaffolded repositories |

---

## 5. Template Skeleton Placeholders (Auto-Substituted by Scaffolder)

These placeholders use the Backstage Nunjucks syntax `${{ values.<parameter> }}` and are **automatically substituted** by the Backstage Scaffolder when a user creates a component through the UI. They do **NOT** require manual editing.

### Common Placeholders (All Templates)

| Pattern | Description | Source |
|---------|-------------|--------|
| `${{ values.name }}` | Component name (e.g., `my-rag-pipeline`) | User input |
| `${{ values.description }}` | Component description | User input |
| `${{ values.owner }}` | Owner team (from catalog Group picker) | User input |
| `${{ values.awsRegion }}` | AWS region (e.g., `us-east-1`) | User input |
| `${{ values.awsAccountId }}` | AWS account ID (from catalog Resource picker) | User input |
| `${{ values.accountId }}` | AWS account ID (VPC template variant) | User input |
| `${{ values.environment }}` | Environment (`dev`, `staging`, `prod`) | User input |
| `${{ values.repoUrl }}` | GitHub repository URL | User input (RepoUrlPicker) |
| `${{ values.destination }}` | Parsed repo URL object (VPC template) | Derived from `repoUrl` |

### VPC Template

| Pattern | Description |
|---------|-------------|
| `${{ values.vpcCidr }}` | VPC CIDR block (e.g., `10.0.0.0/16`) |
| `${{ values.availabilityZones }}` | Number of AZs (2 or 3) |
| `${{ values.enableNatGateway }}` | Whether to create NAT Gateway |
| `${{ values.singleNatGateway }}` | Use single NAT Gateway for cost savings |
| `${{ values.enableVpcEndpoints }}` | Create VPC endpoints for AWS services |

### Bedrock Fine-Tuning Template

| Pattern | Description |
|---------|-------------|
| `${{ values.baseModelId }}` | Bedrock foundation model ID |
| `${{ values.customizationType }}` | `FINE_TUNING` or `CONTINUED_PRE_TRAINING` |
| `${{ values.trainingEpochs }}` | Number of training epochs |
| `${{ values.batchSize }}` | Training batch size |
| `${{ values.learningRate }}` | Training learning rate |
| `${{ values.warmupRatio }}` | Warmup ratio for training |
| `${{ values.enableDataValidation }}` | Validate training data before job start |
| `${{ values.maxTrainingDataSizeMb }}` | Maximum training data size in MB |
| `${{ values.validationDataRatio }}` | Fraction of data for validation |
| `${{ values.enableProvisionedThroughput }}` | Auto-provision model for inference |
| `${{ values.provisionedModelUnits }}` | Number of provisioned model units |
| `${{ values.enableNotifications }}` | Enable SNS notifications |
| `${{ values.notificationEmail }}` | Email address for notifications |

### QnA RAG Pipeline Template

| Pattern | Description |
|---------|-------------|
| `${{ values.vpcId }}` | VPC ID for Lambda deployment |
| `${{ values.privateSubnetIds }}` | Comma-separated private subnet IDs |
| `${{ values.bedrockModelId }}` | Bedrock LLM model for answer generation |
| `${{ values.embeddingModelId }}` | Embedding model for vector generation |
| `${{ values.vectorDimensions }}` | Embedding vector dimensions |
| `${{ values.collectionName }}` | OpenSearch Serverless collection name |
| `${{ values.vectorIndexName }}` | OpenSearch vector index name |

### SageMaker JumpStart Endpoint Template

| Pattern | Description |
|---------|-------------|
| `${{ values.jumpstartModelId }}` | JumpStart model identifier |
| `${{ values.instanceType }}` | SageMaker inference instance type |
| `${{ values.initialInstanceCount }}` | Number of inference instances |
| `${{ values.enableDataCapture }}` | Capture request/response data to S3 |
| `${{ values.dataCapturePercent }}` | Percentage of requests to capture |

### SageMaker HuggingFace Endpoint Template

| Pattern | Description |
|---------|-------------|
| `${{ values.huggingfaceModelId }}` | HuggingFace Hub model ID |
| `${{ values.taskType }}` | Model task type (text-generation, etc.) |
| `${{ values.instanceType }}` | SageMaker inference instance type |
| `${{ values.tgiVersion }}` | Text Generation Inference container version |
| `${{ values.quantization }}` | Quantization method (none, bitsandbytes-nf4, etc.) |

### SageMaker LLM Fine-Tuning Template

| Pattern | Description |
|---------|-------------|
| `${{ values.baseModel }}` | HuggingFace model to fine-tune |
| `${{ values.instanceType }}` | SageMaker training instance type |
| `${{ values.instanceCount }}` | Number of training instances (distributed) |
| `${{ values.epochs }}` | Number of training epochs |
| `${{ values.loraRank }}` | LoRA adapter rank (8, 16, 32, 64) |
| `${{ values.learningRate }}` | LoRA fine-tuning learning rate |
| `${{ values.trainingDataS3Path }}` | S3 path to training data |
| `${{ values.validationSplit }}` | Fraction of data for validation |

### Strands AI Agents on EKS Template

| Pattern | Description |
|---------|-------------|
| `${{ values.eksClusterName }}` | Existing EKS cluster name |
| `${{ values.ecrRepoName }}` | ECR repository name for agent images |
| `${{ values.bedrockModelId }}` | Bedrock model for agent reasoning |

### MLflow AI Gateway Template

| Pattern | Description |
|---------|-------------|
| `${{ values.vpcId }}` | VPC for Fargate service deployment |
| `${{ values.privateSubnetIds }}` | Private subnet IDs for ECS tasks |
| `${{ values.publicSubnetIds }}` | Public subnet IDs for the ALB |
| `${{ values.backendStoreType }}` | Metadata backend (`dynamodb`) |
| `${{ values.artifactBucketName }}` | S3 bucket name for ML artifacts |
| `${{ values.containerCpu }}` | CPU units per Fargate task |
| `${{ values.containerMemory }}` | Memory in MiB per Fargate task |
| `${{ values.desiredCount }}` | Number of Fargate tasks |
| `${{ values.enableAutoScaling }}` | Enable auto-scaling based on CPU |

---

## 6. GitHub Actions Placeholders (Per-Generated-Repo -- Auto-Substituted)

These patterns appear in the generated GitHub Actions workflows (`deploy.yml`, `destroy.yml`) after scaffolding. They are populated from the scaffolded values above.

| Pattern in Generated Repo | Description | Source |
|---------------------------|-------------|--------|
| `arn:aws:iam::<accountId>:role/GitHubActionsDeployRole` | IAM role ARN for OIDC authentication | `values.awsAccountId` or `values.accountId` |
| `AWS_REGION: <region>` | AWS region for CDK deployment | `values.awsRegion` |
| `ENVIRONMENT: <env>` | Deployment environment | `values.environment` |

### IAM Role Prerequisite

The IAM role `GitHubActionsDeployRole` must exist in each target AWS account before the generated workflows can run. This role requires:

1. A trust relationship allowing the GitHub OIDC identity provider
2. Permissions for the CDK resources being deployed
3. The GitHub OIDC identity provider must be registered in the AWS account

Example trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<GITHUB_ORG>/*:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

---

## 7. Files Containing Placeholders by Location

For quick reference, this is the complete list of skeleton files that contain `${{ values.* }}` placeholders:

### Catalog Info Files (per template)

- `templates/foundation/vpc/skeleton/catalog-info.yaml`
- `templates/fmops/bedrock-finetuning/skeleton/catalog-info.yaml`
- `templates/fmops/qna-rag/skeleton/catalog-info.yaml`
- `templates/fmops/sagemaker-jumpstart-endpoint/skeleton/catalog-info.yaml`
- `templates/fmops/sagemaker-huggingface-endpoint/skeleton/catalog-info.yaml`
- `templates/fmops/sagemaker-llm-finetune/skeleton/catalog-info.yaml`
- `templates/agents/eks-strands-agents/skeleton/catalog-info.yaml`
- `templates/mlflow/ai-gateway/skeleton/catalog-info.yaml`

### CDK App Entry Points (per template)

- `templates/foundation/vpc/skeleton/cdk/app.py`
- `templates/fmops/bedrock-finetuning/skeleton/cdk/app.py`
- `templates/fmops/qna-rag/skeleton/cdk/app.py`
- `templates/fmops/sagemaker-jumpstart-endpoint/skeleton/cdk/app.py`
- `templates/fmops/sagemaker-huggingface-endpoint/skeleton/cdk/app.py`
- `templates/fmops/sagemaker-llm-finetune/skeleton/cdk/app.py`
- `templates/agents/eks-strands-agents/skeleton/cdk/app.py`
- `templates/mlflow/ai-gateway/skeleton/cdk/app.py`

### GitHub Actions Workflows (per template)

- `templates/*/skeleton/.github/workflows/deploy.yml` (all 8 templates)
- `templates/*/skeleton/.github/workflows/destroy.yml` (all 8 templates)

### README Files (per template)

- `templates/*/skeleton/README.md` (all 8 templates)

### Agent Source Code

- `templates/agents/eks-strands-agents/skeleton/agent/agent.py` (contains `${{ values.bedrockModelId }}`)
