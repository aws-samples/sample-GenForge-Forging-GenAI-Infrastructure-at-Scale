# GenForge

**Forging GenAI infrastructure at scale**

> ⚠️ **Important**: This project is provided as sample/educational code and is NOT intended
> for production use without additional security hardening. See [SECURITY.md](./SECURITY.md)
> for production hardening recommendations.

GenForge is an Internal Developer Platform (IDP) built on [Backstage](https://backstage.io/) (v1.48.0) for self-service GenAI infrastructure provisioning. Data scientists and ML engineers can provision reference AWS infrastructure through guided UI workflows -- without writing infrastructure code.

Users fill out a form, GenForge generates a GitHub repository with CDK Python code and GitHub Actions workflows, and infrastructure deploys automatically via OIDC -- no long-lived credentials, no manual IaC authoring.

## Prerequisites

### Local Development Tools

| Tool | Version | Installation |
|------|---------|-------------|
| Node.js | 22+ (or 24) | `brew install node@22` or [nodejs.org](https://nodejs.org/) |
| Yarn | 4.4.1 | `corepack enable && corepack prepare yarn@4.4.1 --activate` |
| Python | 3.11+ | `brew install python@3.11` or [python.org](https://www.python.org/) |
| AWS CDK CLI | 2.170.0 (pinned) | `npm install -g aws-cdk@2.170.0` |
| AWS CLI | v2 | `brew install awscli` or [AWS docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| Docker | Latest | Required for EKS Strands Agents and MLflow templates |

### GitHub Setup

#### 1. GitHub Personal Access Token (PAT)

Backstage needs a PAT to create repositories via the `publish:github` scaffolder step.

Create a **Fine-grained PAT** or **Classic PAT** at https://github.com/settings/tokens with these scopes:

| Scope | Why |
|-------|-----|
| `repo` | Full control of private repositories (create repos, push skeleton code) |
| `workflow` | Create `.github/workflows/` files in scaffolded repos |
| `delete_repo` | Optional -- only if you want cleanup capability |
| `admin:org` | Only if creating repos under a GitHub Organization |

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> Without this token, the Backstage scaffolder will fail at the "Publish to GitHub" step.

#### 2. GitHub OAuth App (Required for CI/CD tab)

The GitHub Actions plugin on the component details page requires GitHub OAuth to fetch workflow runs.

1. Go to https://github.com/settings/developers
2. Click **New OAuth App**
3. Fill in:
   - **Application name:** `GenForge`
   - **Homepage URL:** `http://localhost:3000`
   - **Authorization callback URL:** `http://localhost:7007/api/auth/github/handler/frame`
4. Click **Register application**
5. Copy the **Client ID** and generate + copy the **Client Secret**

```bash
export GITHUB_CLIENT_ID=Ov23lixxxxxxxxxx
export GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> Without this, the CI/CD tab on component pages will show a "Sign in" prompt that fails.

#### 3. GitHub Organization (Recommended)

Templates use `RepoUrlPicker` scoped to `github.com`. For team usage, configure your GitHub org name so repos are created under the org rather than personal accounts.

### AWS Setup

Every scaffolded repository deploys infrastructure via GitHub Actions using OIDC (no static AWS keys). This requires **one-time setup per AWS account**.

#### 1. Register GitHub OIDC Identity Provider in IAM

This allows GitHub Actions to request temporary AWS credentials:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

> Run this once per AWS account. If it already exists, the command will return an error (safe to ignore).

#### 2. Create the IAM Deploy Role

All 8 templates reference a role named `GitHubActionsDeployRole`. Create it with this trust policy:

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

Replace `<ACCOUNT_ID>` with your AWS account ID and `<GITHUB_ORG>` with your GitHub org name.

The role needs permissions to create resources for the templates you plan to use:

| Template | IAM Permissions Required on Deploy Role |
|----------|----------------------------------------|
| VPC | `ec2:*` (VPC, subnets, NAT, endpoints, security groups, flow logs), `logs:*`, `iam:*`, `kms:*` |
| Bedrock Fine-Tuning | `bedrock:*`, `s3:*`, `lambda:*`, `states:*`, `sns:*`, `logs:*`, `iam:*`, `kms:*` |
| QnA RAG | `aoss:*`, `cognito-idp:*`, `lambda:*`, `s3:*`, `bedrock:*`, `logs:*`, `iam:*`, `kms:*`, `ec2:Describe*` |
| SageMaker JumpStart | `sagemaker:*`, `s3:*`, `ecr:*`, `cloudwatch:*`, `logs:*`, `iam:*`, `kms:*` |
| SageMaker HuggingFace | `sagemaker:*`, `s3:*`, `ecr:*`, `cloudwatch:*`, `application-autoscaling:*`, `logs:*`, `iam:*`, `kms:*` |
| SageMaker LLM Fine-Tune | `sagemaker:*`, `s3:*`, `lambda:*`, `states:*`, `logs:*`, `iam:*`, `kms:*` |
| EKS Strands Agents | `ecr:*`, `iam:*`, `logs:*`, `bedrock:*`, `kms:*` |
| MLflow AI Gateway | `ecs:*`, `ecr:*`, `elasticloadbalancing:*`, `s3:*`, `dynamodb:*`, `bedrock:*`, `application-autoscaling:*`, `logs:*`, `iam:*`, `kms:*`, `ec2:Describe*` |

> For a simpler (but less secure) setup, attach `AdministratorAccess` to the deploy role during development, then scope down permissions before production use.

#### 3. Bootstrap AWS CDK

CDK requires a one-time bootstrap per account+region. This creates the `CDKToolkit` CloudFormation stack with an S3 bucket and IAM roles that CDK uses internally:

```bash
# Authenticate to the target account first
aws sts get-caller-identity  # verify correct account

# Bootstrap each account+region combination you plan to deploy to
cdk bootstrap aws://111111111111/us-east-1
cdk bootstrap aws://111111111111/us-west-2
```

#### 4. Update AWS Account IDs in Catalog

Replace placeholder account IDs in `catalog/aws-accounts.yaml`:

```yaml
# Replace these with your real AWS account IDs
# 111111111111 -> your dev account
# 222222222222 -> your staging account
# 333333333333 -> your prod account
```

### AWS Service-Specific Prerequisites

Some templates require additional AWS service setup beyond IAM permissions:

#### Amazon Bedrock Model Access

**Required by:** Bedrock Fine-Tuning, QnA RAG, EKS Strands Agents, MLflow AI Gateway

Bedrock models are not enabled by default. You must request access in the AWS console:

1. Go to **Amazon Bedrock** > **Model access** in your target region
2. Click **Manage model access**
3. Enable the models your templates will use:

| Template | Models to Enable |
|----------|-----------------|
| Bedrock Fine-Tuning | Titan Text Express/Lite, Claude 3 Haiku, Cohere Command, Llama 2 |
| QnA RAG | Claude 3 Sonnet/Haiku, Titan Text Express, Cohere Command (LLM) + Titan Embed, Cohere Embed (embeddings) |
| EKS Strands Agents | Claude 3 Sonnet/Haiku, Titan Text Express |
| MLflow AI Gateway | Any Bedrock models the gateway will proxy |

> Model access approval can be instant for some models (Titan) or require justification for others (Claude, Llama).

#### SageMaker Instance Quotas

**Required by:** SageMaker JumpStart, SageMaker HuggingFace, SageMaker LLM Fine-Tuning

GPU instance quotas default to **0** in most accounts. Request increases before deploying:

1. Go to **Service Quotas** > **Amazon SageMaker**
2. Search for quotas by instance type:

| Quota Name | Instance | Default | Templates |
|------------|----------|---------|-----------|
| `ml.g5.xlarge for endpoint usage` | ml.g5.xlarge | 0 | JumpStart, HuggingFace |
| `ml.g5.2xlarge for endpoint usage` | ml.g5.2xlarge | 0 | JumpStart, HuggingFace |
| `ml.g5.xlarge for training job usage` | ml.g5.xlarge | 0 | LLM Fine-Tuning |
| `ml.g5.2xlarge for training job usage` | ml.g5.2xlarge | 0 | LLM Fine-Tuning |
| `ml.p4d.24xlarge for endpoint usage` | ml.p4d.24xlarge | 0 | JumpStart, HuggingFace |
| `ml.p4d.24xlarge for training job usage` | ml.p4d.24xlarge | 0 | LLM Fine-Tuning |

> Request only the instance types you plan to use. Quota increases typically take 1-3 business days for GPU instances.

#### HuggingFace Model Licenses

**Required by:** SageMaker HuggingFace Endpoint, SageMaker LLM Fine-Tuning

Some HuggingFace models are gated and require license acceptance:

| Model | License | Action |
|-------|---------|--------|
| `meta-llama/Llama-2-*` | Meta Llama 2 Community License | Accept at https://huggingface.co/meta-llama |
| `codellama/CodeLlama-*` | Meta Llama 2 Community License | Accept at https://huggingface.co/codellama |
| `mistralai/Mistral-*` | Apache 2.0 | No action needed (open) |
| `tiiuae/falcon-*` | Apache 2.0 | No action needed (open) |

#### Existing EKS Cluster

**Required by:** Strands AI Agents on EKS

This template does NOT create an EKS cluster. You must have:

- A running EKS cluster with an OIDC identity provider configured (for IRSA)
- `kubectl` and `helm` access to the cluster (for post-CDK Helm deployment)
- The cluster's OIDC provider ID (found in the EKS console under the cluster's Configuration > Details)

#### Existing VPC

**Required by:** QnA RAG Pipeline, MLflow AI Gateway

These templates require an existing VPC with subnets. Use the **VPC Foundation** template to create one first, or provide IDs from an existing VPC:

| Template | Required Network Inputs |
|----------|------------------------|
| QnA RAG | VPC ID (`vpc-xxx`), private subnet IDs (`subnet-xxx,subnet-yyy`) |
| MLflow AI Gateway | VPC ID (`vpc-xxx`), private subnet IDs, **and** public subnet IDs (for ALB) |

### Template Dependency Graph

```
VPC Foundation  (deploy first -- no dependencies)
 |
 +---> QnA RAG Pipeline          (needs VPC ID + private subnets)
 +---> MLflow AI Gateway         (needs VPC ID + private + public subnets)

EKS Cluster  (external -- not a GenForge template)
 |
 +---> Strands AI Agents on EKS  (needs existing cluster name + OIDC provider)

Standalone  (no infrastructure dependencies)
 +-- Bedrock Fine-Tuning
 +-- SageMaker JumpStart Endpoint
 +-- SageMaker HuggingFace Endpoint
 +-- SageMaker LLM Fine-Tuning
```

### Setup Checklist

Use this checklist before your first template deployment:

- [ ] Node.js 22+, Yarn 4.4.1, Python 3.11+, AWS CDK CLI installed
- [ ] GitHub PAT created with `repo` + `workflow` scopes
- [ ] GitHub OAuth App created (Client ID + Client Secret)
- [ ] `GITHUB_TOKEN`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` environment variables exported
- [ ] GitHub OIDC Identity Provider created in target AWS account(s)
- [ ] `GitHubActionsDeployRole` IAM role created with trust policy + permissions
- [ ] `cdk bootstrap` run in target account+region
- [ ] Real AWS account IDs updated in `catalog/aws-accounts.yaml`
- [ ] Bedrock model access enabled (if using Bedrock/RAG/Agents/MLflow templates)
- [ ] SageMaker GPU instance quotas increased (if using SageMaker templates)
- [ ] HuggingFace model licenses accepted (if using gated models)
- [ ] VPC deployed via VPC template (if using QnA RAG or MLflow templates)
- [ ] EKS cluster running with OIDC provider (if using Strands Agents template)

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url> genforge
cd genforge

# Install all dependencies
yarn install

# Set required environment variables
export GITHUB_TOKEN=ghp_your_token_here              # PAT with repo + workflow scopes
export GITHUB_CLIENT_ID=Ov23lixxxxxxxxxx              # GitHub OAuth App Client ID
export GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx  # GitHub OAuth App Client Secret

# Start the development server (frontend + backend)
yarn start
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:7007 |
| Scaffolder (Create) | http://localhost:3000/create |
| Software Catalog | http://localhost:3000/catalog |
| TechDocs | http://localhost:3000/docs |
| Search | http://localhost:3000/search |

In development mode, authentication uses the guest provider -- no login credentials are required.

## Template Catalog

GenForge ships with 8 reference templates organized into 4 categories:

| Category | Template | Description | AWS Services |
|----------|----------|-------------|--------------|
| **Foundation** | VPC | Production VPC with public/private/isolated subnets, NAT gateways, and VPC endpoints for GenAI services | VPC, Subnets, NAT GW, VPC Endpoints |
| **FMOps** | Bedrock Fine-Tuning | Fine-tune foundation models with Amazon Bedrock using Step Functions orchestration | Bedrock, S3, Lambda, Step Functions, SNS |
| **FMOps** | QnA RAG Pipeline | RAG solution with Bedrock LLMs, OpenSearch Serverless vector store, and document ingestion | Bedrock, OpenSearch Serverless, Lambda, S3, Cognito |
| **FMOps** | SageMaker JumpStart Endpoint | Deploy 400+ pre-trained models (Llama, Falcon, Mistral) as real-time inference endpoints | SageMaker, CloudWatch |
| **FMOps** | SageMaker HuggingFace Endpoint | Deploy HuggingFace Hub models with Text Generation Inference (TGI) container | SageMaker, ECR, CloudWatch |
| **FMOps** | SageMaker LLM Fine-Tuning | Fine-tune LLMs with LoRA/QLoRA on SageMaker with distributed training support | SageMaker, S3, Lambda, Step Functions |
| **AI Agents** | Strands on EKS | Deploy AI agents with the Strands framework on Amazon EKS with Bedrock LLM backend | EKS, ECR, Bedrock, IAM |
| **MLflow** | AI Gateway | MLflow AI Gateway on ECS Fargate with experiment tracking, artifact storage, and auto-scaling | ECS Fargate, ALB, ECR, S3, DynamoDB |

## Architecture

### Provisioning Flow

```
+------------------+     +---------------------+     +--------------------+
|  1. User selects |     |  2. Backstage        |     |  3. GitHub Actions |
|     template and | --> |     Scaffolder runs:  | --> |     triggers:      |
|     fills form   |     |     fetch:template    |     |     OIDC auth      |
|                  |     |     publish:github     |     |     cdk deploy     |
|                  |     |     catalog:register   |     |     infrastructure |
|                  |     |                       |     |     is live         |
+------------------+     +---------------------+     +--------------------+
```

1. **User selects template** in the Backstage UI and fills out a guided multi-step form (component info, AWS config, template-specific parameters, repository location)
2. **Backstage Scaffolder** interpolates parameters into skeleton files, publishes a new GitHub repository, and registers the component in the Backstage catalog
3. **GitHub Actions** triggers on push to `main`: authenticates to AWS via OIDC, runs `cdk deploy`, and provisions all infrastructure

### Project Structure

```
genforge/
+-- packages/
|   +-- app/                              # Frontend React app (port 3000)
|   |   +-- src/
|   |       +-- App.tsx                   # Routes, template groups, plugin bindings
|   |       +-- components/Root/          # Sidebar navigation
|   +-- backend/                          # Backend Node.js app (port 7007)
|       +-- src/
|           +-- index.ts                  # Plugin registration
+-- templates/                            # 8 scaffolder templates
|   +-- foundation/
|   |   +-- vpc/
|   |       +-- template.yaml             # Scaffolder definition
|   |       +-- skeleton/                 # Files scaffolded into new repos
|   |           +-- cdk/                  # CDK Python stack (app.py, stack.py)
|   |           +-- .github/workflows/    # deploy.yml, destroy.yml
|   |           +-- catalog-info.yaml     # Backstage catalog registration
|   +-- fmops/
|   |   +-- bedrock-finetuning/
|   |   +-- qna-rag/
|   |   +-- sagemaker-jumpstart-endpoint/
|   |   +-- sagemaker-huggingface-endpoint/
|   |   +-- sagemaker-llm-finetune/
|   +-- agents/
|   |   +-- eks-strands-agents/
|   +-- mlflow/
|       +-- ai-gateway/
+-- catalog/                              # Backstage catalog entities
|   +-- genforge-system.yaml              # System entity
|   +-- org.yaml                          # Groups and users
|   +-- aws-accounts.yaml                 # AWS account resources
+-- docs/                                 # TechDocs documentation
+-- app-config.yaml                       # Main Backstage configuration
+-- app-config.production.yaml            # Production overrides (PostgreSQL, GitHub OAuth)
+-- package.json                          # Root workspace config (Yarn 4.4.1)
+-- tsconfig.json                         # TypeScript configuration
+-- playwright.config.ts                  # E2E test configuration
+-- backstage.json                        # Backstage version (1.48.0)
```

### Backend Plugins

The following Backstage backend plugins are registered in `packages/backend/src/index.ts`:

| Category | Plugins |
|----------|---------|
| Core | `plugin-app-backend`, `plugin-proxy-backend` |
| Scaffolder | `plugin-scaffolder-backend`, `plugin-scaffolder-backend-module-github`, `plugin-scaffolder-backend-module-notifications` |
| TechDocs | `plugin-techdocs-backend` |
| Auth | `plugin-auth-backend`, `plugin-auth-backend-module-guest-provider`, `plugin-auth-backend-module-github-provider` |
| Catalog | `plugin-catalog-backend`, `plugin-catalog-backend-module-scaffolder-entity-model`, `plugin-catalog-backend-module-logs` |
| Permission | `plugin-permission-backend`, `plugin-permission-backend-module-allow-all-policy` |
| Search | `plugin-search-backend`, `plugin-search-backend-module-pg`, `plugin-search-backend-module-catalog`, `plugin-search-backend-module-techdocs` |
| Notifications | `plugin-notifications-backend`, `plugin-signals-backend` |

### Frontend Routes

| Route | Page |
|-------|------|
| `/catalog` | Software Catalog |
| `/create` | Scaffolder (template selection with 4 groups: Foundation, Generative AI & FMOps, AI Agents, MLflow) |
| `/docs` | TechDocs |
| `/search` | Search |
| `/api-docs` | API Explorer |
| `/settings` | User Settings |
| `/notifications` | Notifications |
| `/catalog-graph` | Catalog Graph |

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token (`repo` + `workflow` scopes) for scaffolder and GitHub integration |
| `GITHUB_CLIENT_ID` | Yes | GitHub OAuth App Client ID (required for CI/CD tab on component pages) |
| `GITHUB_CLIENT_SECRET` | Yes | GitHub OAuth App Client Secret |
| `POSTGRES_HOST` | Yes (prod) | PostgreSQL host for production database |
| `POSTGRES_PORT` | Yes (prod) | PostgreSQL port (default: 5432) |
| `POSTGRES_USER` | Yes (prod) | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes (prod) | PostgreSQL password |

### AWS Setup

See the [Prerequisites > AWS Setup](#aws-setup) section above for complete instructions on OIDC provider, IAM deploy role, CDK bootstrap, and service-specific requirements.

### Database

| Environment | Backend | Configuration |
|-------------|---------|---------------|
| Development | SQLite (file-based) | Persists to `.backstage-db/` directory, survives restarts |
| Production | PostgreSQL | Set `POSTGRES_*` env vars, use `app-config.production.yaml` |

## Development

### Build Commands

```bash
yarn install              # Install all dependencies
yarn start                # Start frontend (3000) + backend (7007) concurrently
yarn build:backend        # Build backend package
yarn build:all            # Build all packages
yarn build-image          # Build Docker image for backend
yarn tsc                  # TypeScript compile (incremental)
yarn tsc:full             # Full TypeScript compile (strict, no skipLibCheck)
yarn clean                # Clean build artifacts
yarn new                  # Create new Backstage package/plugin via wizard
```

### Testing

```bash
yarn test                 # Run unit tests (changed files only)
yarn test:all             # Run all tests with coverage
yarn test:e2e             # Run Playwright end-to-end tests
```

### Linting and Formatting

```bash
yarn lint                 # Lint changes since origin/main
yarn lint:all             # Lint entire codebase
yarn fix                  # Auto-fix lint issues
yarn prettier:check       # Check formatting (Prettier)
```

### CDK Template Development

Each template skeleton contains a standalone CDK Python project under `skeleton/cdk/`:

```bash
cd templates/<category>/<template>/skeleton/cdk/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk synth     # Synthesize CloudFormation template
cdk diff      # Preview changes
cdk deploy    # Deploy (requires AWS credentials)
```

## Security Controls

Every template generated by GenForge embeds the following security controls:

| Control | Implementation |
|---------|---------------|
| **No long-lived credentials** | GitHub Actions OIDC federation with AWS IAM roles |
| **Encryption at rest** | SSE-KMS for S3 buckets, encrypted EBS volumes, encrypted DynamoDB tables |
| **Encryption in transit** | TLS enforced on all endpoints and load balancers |
| **Network isolation** | VPC with private subnets, VPC endpoints for AWS service access without internet |
| **Least-privilege IAM** | Scoped IAM policies per service, no wildcard permissions |
| **Resource tagging** | Consistent tags: `Name`, `environment`, `owner`, `genforge:managed=true` |
| **Removal policies** | `DESTROY` for dev environments, `RETAIN` for staging/production |
| **Destroy safeguard** | Manual `workflow_dispatch` with "destroy" confirmation required |

## Naming Conventions

| Entity | Pattern | Example |
|--------|---------|---------|
| Template name | `genforge-<template>-template` | `genforge-vpc-template` |
| Template spec.type | `foundation` / `fmops` / `agents` / `mlflow` | `fmops` |
| CDK stack name | `<component>-<env>-stack` | `my-rag-dev-stack` |
| AWS resource name | `<component>-<env>-<resource>` | `my-rag-dev-documents-bucket` |
| Component name | `^[a-z0-9-]+$` (max 50 chars) | `my-bedrock-finetuning` |

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Platform Framework | Backstage | 1.48.0 |
| Frontend | React + TypeScript | React 18 / TypeScript 5.8 |
| Backend | Node.js | 22+ |
| Infrastructure as Code | AWS CDK (Python) | 2.170.0+ |
| CI/CD | GitHub Actions | OIDC authentication |
| Package Manager | Yarn | 4.4.1 |
| Database | SQLite (dev) / PostgreSQL (prod) | -- |
| Auth | Guest (dev) / GitHub OAuth (prod) | -- |
| Testing | Playwright (e2e) + Jest (unit) | -- |

## License

This project is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file for details.
