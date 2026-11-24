# ${{ values.name }} - Strands AI Agent on EKS

Deploy AI agents using the Strands framework on Amazon EKS with Bedrock as the LLM backend.

## Architecture

```
+-------------------------------------------------------------------------+
|                     Strands AI Agent on EKS                             |
|                                                                         |
|  +-------------------+     +-------------------+     +--------------+   |
|  |   EKS Cluster     |     |   Amazon Bedrock  |     |  CloudWatch  |   |
|  |   (${{ values.eksClusterName }})  |---->|   (LLM Backend)   |     |  (Logs)      |   |
|  |                   |     |                   |     |              |   |
|  |  +-------------+  |     | Model:            |     +--------------+   |
|  |  | Strands     |  |     | ${{ values.bedrockModelId }} |          |
|  |  | Agent Pod   |  |     +-------------------+                       |
|  |  +-------------+  |                                                  |
|  |        |          |                                                  |
|  |  +-------------+  |     +-------------------+                       |
|  |  | Service     |  |     |   ECR Repository  |                       |
|  |  | Account     |  |     |   (Agent Image)   |                       |
|  |  | (IRSA)      |  |     +-------------------+                       |
|  |  +-------------+  |                                                  |
|  +-------------------+                                                  |
+-------------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| EKS Cluster | ${{ values.eksClusterName }} |
| ECR Repository | ${{ values.ecrRepoName }} |
| Bedrock Model | ${{ values.bedrockModelId }} |

## One-Time Setup (Required)

Before deploying, you need to create the GitHub OIDC provider and IAM role in AWS. This is done ONCE for your entire GitHub organization.

### Prerequisites

1. **AWS CLI** installed and configured
2. **AWS CDK** installed (`npm install -g aws-cdk`)
3. **AWS Credentials** with permissions to:
   - Create IAM OIDC providers
   - Create and manage IAM roles
   - Attach IAM policies
   - Bootstrap CDK (CloudFormation, S3, etc.)
   - Prefer an IAM role with a scoped policy covering the specific IAM,
     CloudFormation, S3, and OIDC provider actions required to bootstrap CDK
     and deploy the stack. Avoid using broad managed policies such as
     `IAMFullAccess` or `AdministratorAccess`; scope permissions to the
     minimum needed for your account.

### Step 1: Bootstrap CDK (First Time Only)

If you haven't used CDK in this AWS account/region before, bootstrap it:

```bash
# Export your AWS credentials
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Bootstrap CDK (replace with your account ID and region)
cdk bootstrap aws://${{ values.awsAccountId }}/${{ values.awsRegion }}
```

**What CDK bootstrap does:**
- Creates an S3 bucket for CDK assets
- Creates IAM roles for CloudFormation
- Sets up necessary infrastructure for CDK deployments
- Only needs to be done once per AWS account/region combination

**Check if already bootstrapped:**
```bash
aws ssm get-parameter --name /cdk-bootstrap/hnb659fds/version --region ${{ values.awsRegion }}
```
If this returns a value, CDK is already bootstrapped.

### Step 2: Run OIDC Setup Script

### Step 2: Run OIDC Setup Script

```bash
# 1. Ensure AWS credentials are still exported (from Step 1)
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key

# 2. Clone this repository (if not already cloned)
git clone https://github.com/${{ values.githubOrg }}/${{ values.githubRepo }}.git
cd ${{ values.githubRepo }}

# 3. Run the setup script with your GitHub org, AWS account ID, and region
chmod +x scripts/setup-github-oidc.sh
./scripts/setup-github-oidc.sh ${{ values.githubOrg }} ${{ values.awsAccountId }} ${{ values.awsRegion }}
```

**What the script does:**
- Creates GitHub OIDC Provider in AWS IAM (if not exists)
- Creates IAM Role: `GitHubActionsDeployRole`
- Sets trust policy allowing all repos in your GitHub organization: `repo:${{ values.githubOrg }}/*:ref:refs/*`
- Attaches necessary permissions:
  - Custom CDK deployment policy (see setup script for scoped, region-locked permissions)
  - `IAMPassRolePolicy` (scoped `iam:PassRole` for CDK deployments)

**After this one-time setup:**
- ALL repositories in your organization can deploy using OIDC
- No AWS access keys needed in GitHub secrets
- More secure than long-lived credentials

> **Security note**: The default trust policy allows any repo in the org and any branch (`repo:<org>/*:ref:refs/*`). Before production use, narrow this to specific repositories and branches, for example `repo:<org>/<repo>:ref:refs/heads/main`.

## Deployment

Once the OIDC setup is complete, simply push to main:

```bash
git push origin main
```

Or trigger manually:

```bash
gh workflow run deploy.yml
```

The workflow will:
1. Authenticate using OIDC (no access keys!)
2. Deploy CDK stack (ECR, IAM roles, CloudWatch logs)
3. Build and push Docker image to ECR

## Prerequisites

- **One-time OIDC setup** (see above)
- **EKS Cluster** - An existing EKS cluster with OIDC provider enabled
- **Bedrock Access** - Model access granted in the Bedrock console
- **kubectl/Helm** - CLI tools for Kubernetes deployment

## Support

For issues, contact the ${{ values.owner }} team.
