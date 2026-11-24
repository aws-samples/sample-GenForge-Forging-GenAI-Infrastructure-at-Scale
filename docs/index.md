# GenForge Documentation

Welcome to the GenForge documentation. GenForge is an Internal Developer Platform (IDP) built on [Backstage](https://backstage.io/) for self-service GenAI infrastructure provisioning on AWS.

## Getting Started

### Prerequisites

- Node.js 22+ and Yarn 4.4.1
- Python 3.11+ and AWS CDK CLI
- A GitHub Personal Access Token with repo permissions

### Quick Start

```bash
yarn install
export GITHUB_TOKEN=ghp_your_token_here
yarn start
```

Once running, open [http://localhost:3000](http://localhost:3000) in your browser. Navigate to **Create** in the sidebar to browse available templates. In development mode, authentication uses the guest provider automatically.

### First Provisioning

1. Click **Create** in the left sidebar
2. Choose a template from one of the four categories (Foundation, Generative AI & FMOps, AI Agents, MLflow)
3. Fill out the guided form: component information, AWS configuration, template-specific parameters, and repository location
4. Click **Create** -- GenForge generates a GitHub repository with CDK code and CI/CD workflows
5. The GitHub Actions workflow runs automatically, deploying infrastructure to your AWS account via OIDC

---

## Templates

GenForge provides 8 reference templates across 4 categories.

### Foundation

| Template | Description |
|----------|-------------|
| [VPC Foundation](../templates/foundation/vpc/template.yaml) | Multi-tier VPC with public, private, and isolated subnets across multiple AZs. Includes NAT gateways and VPC endpoints for S3, ECR, SageMaker, Bedrock, and other GenAI services. Prerequisite for templates that require VPC deployment (RAG, MLflow, Agents). |

### Generative AI & FMOps

| Template | Description |
|----------|-------------|
| [Bedrock Fine-Tuning](../templates/fmops/bedrock-finetuning/template.yaml) | Fine-tune foundation models (Titan, Claude, Llama, Cohere) with Amazon Bedrock. Includes S3 buckets for training data, Lambda functions for data validation and job management, Step Functions for orchestration, and SNS notifications. Supports both fine-tuning and continued pre-training. |
| [QnA RAG Pipeline](../templates/fmops/qna-rag/template.yaml) | Build a Retrieval-Augmented Generation solution with Bedrock LLMs and OpenSearch Serverless. Includes document ingestion pipeline (chunking, embedding, indexing), query Lambda function, Cognito authentication, and configurable embedding models. Requires a VPC. |
| [SageMaker JumpStart Endpoint](../templates/fmops/sagemaker-jumpstart-endpoint/template.yaml) | Deploy pre-trained models from the SageMaker JumpStart catalog (400+ models including Llama, Falcon, Mistral) as real-time inference endpoints. Optional data capture for model monitoring and CloudWatch alarms. |
| [SageMaker HuggingFace Endpoint](../templates/fmops/sagemaker-huggingface-endpoint/template.yaml) | Deploy any HuggingFace Hub model on SageMaker using the Text Generation Inference (TGI) container. Supports multiple TGI versions, quantization methods (NF4, FP4, GPTQ), and auto-scaling. |
| [SageMaker LLM Fine-Tuning](../templates/fmops/sagemaker-llm-finetune/template.yaml) | Fine-tune LLMs (Llama 2, CodeLlama, Mistral, Falcon) with LoRA on SageMaker. Supports distributed training across multiple GPU instances, configurable LoRA rank, and Step Functions orchestration. |

### AI Agents

| Template | Description |
|----------|-------------|
| [Strands AI Agents on EKS](../templates/agents/eks-strands-agents/template.yaml) | Deploy AI agents using the Strands SDK on an existing Amazon EKS cluster. Includes a weather agent demo with tool calling, ECR repository for container images, IAM role for EKS pod identity with Bedrock access, and Kubernetes manifests. |

### MLflow

| Template | Description |
|----------|-------------|
| [MLflow AI Gateway](../templates/mlflow/ai-gateway/template.yaml) | Run MLflow AI Gateway on ECS Fargate with full experiment tracking and model serving. Includes ALB, ECR repository, S3 artifact storage with KMS encryption, DynamoDB for experiment metadata, and auto-scaling. Requires a VPC. |

---

## Architecture

### High-Level Overview

GenForge follows a three-stage provisioning flow:

```
User (Browser)          Backstage Platform           AWS Cloud
     |                        |                         |
     |  1. Select template    |                         |
     |     & fill form        |                         |
     |----------------------->|                         |
     |                        |  2. Generate repo       |
     |                        |     (CDK + workflows)   |
     |                        |------------------------>|  GitHub
     |                        |                         |
     |                        |  3. Register in catalog |
     |                        |---.                     |
     |                        |   |                     |
     |                        |<--'                     |
     |                        |                         |
     |                        |     4. GitHub Actions   |
     |                        |        OIDC auth +      |
     |                        |        cdk deploy       |
     |                        |           .------------>|  AWS Account
     |                        |           |             |  (VPC, SageMaker,
     |                        |           |             |   Bedrock, ECS, etc.)
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Platform Framework | Backstage 1.48.0 |
| Frontend | React 18 + TypeScript 5.8 |
| Backend | Node.js 22+ |
| Infrastructure as Code | AWS CDK with Python 3.11+ |
| CI/CD | GitHub Actions with OIDC |
| Package Manager | Yarn 4.4.1 (workspaces) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | Guest (dev) / GitHub OAuth (prod) |

### Catalog Model

GenForge uses the Backstage Software Catalog to track:

- **System**: `genforge` -- the platform itself
- **Templates**: 8 scaffolder templates, organized by `spec.type` (`foundation`, `fmops`, `agents`, `mlflow`)
- **Components**: Each provisioned infrastructure component, registered automatically during scaffolding
- **Resources**: AWS accounts available as deployment targets
- **Groups**: Teams that own components (platform-team, data-science-team, data-engineering-team, devops-team)

---

## Security

### Security Model

GenForge enforces security at every layer of the provisioning pipeline:

**Authentication and Authorization**

- Development: Guest provider for local testing
- Production: GitHub OAuth for user authentication
- AWS: OIDC federation -- GitHub Actions authenticates to AWS without long-lived credentials
- Backstage: Permission framework enabled with allow-all policy (customizable)

**Infrastructure Security (Embedded in Every Template)**

- **Encryption at rest**: All S3 buckets use SSE-KMS, DynamoDB tables are encrypted, EBS volumes are encrypted
- **Encryption in transit**: TLS enforced on all load balancers, API endpoints, and service-to-service communication
- **Network isolation**: Private subnets for compute workloads, VPC endpoints for AWS service access without traversing the internet
- **Least-privilege IAM**: Each CDK stack creates scoped IAM roles with only the permissions required for that specific workload
- **Resource tagging**: All resources tagged with `Name`, `environment`, `owner`, and `genforge:managed=true` for governance and cost tracking
- **Environment-aware removal policies**: `DESTROY` for dev (easy cleanup), `RETAIN` for staging and production (data protection)
- **Destroy safeguard**: The `destroy.yml` workflow requires manual `workflow_dispatch` trigger with explicit "destroy" confirmation input

**Supply Chain Security**

- All GitHub Actions use pinned versions (`actions/checkout@v4`, `aws-actions/configure-aws-credentials@v4`, etc.)
- CDK dependencies are pinned in `requirements.txt` per template
- No long-lived secrets stored in repositories -- OIDC handles all AWS authentication

---

## Additional Resources

- [Placeholder Locations](./PLACEHOLDER-LOCATIONS.md) -- Complete list of all configuration placeholders requiring substitution
- [Backstage Documentation](https://backstage.io/docs) -- Official Backstage platform documentation
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/) -- AWS CDK Python API reference
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) -- Setting up OIDC for AWS
