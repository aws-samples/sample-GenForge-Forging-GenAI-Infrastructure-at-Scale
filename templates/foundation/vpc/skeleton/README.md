# ${{ values.name }}

${{ values.description | default("VPC Foundation Infrastructure provisioned by GenForge.") }}

## Architecture

This VPC is designed for GenAI workloads on AWS, providing network isolation with three subnet tiers across ${{ values.availabilityZones }} availability zones.

```
+-----------------------------------------------------------------+
|                        VPC (${{ values.vpcCidr }})                          |
|                                                                 |
|  +------------------+  +------------------+  +------------------+
|  |  Public Subnets  |  |  Private Subnets |  | Isolated Subnets |
|  |                  |  |                  |  |                  |
|  |  - NAT Gateway   |  |  - ML Workloads  |  |  - Databases     |
|  |  - Load Balancers|  |  - EKS Nodes     |  |  - ElastiCache   |
|  |  - Bastion Hosts |  |  - Lambda        |  |  - OpenSearch    |
|  +------------------+  +------------------+  +------------------+
|                                                                 |
|  VPC Endpoints: S3, DynamoDB, SageMaker, Bedrock, ECR,         |
|                 CloudWatch Logs, SSM, STS, KMS, Secrets Manager |
+-----------------------------------------------------------------+
```

### Subnet Tiers

| Tier | Type | Internet Access | Use Cases |
|------|------|----------------|-----------|
| Public | PUBLIC | Direct (IGW) | NAT Gateways, Load Balancers, Bastion Hosts |
| Private | PRIVATE_WITH_EGRESS | Outbound via NAT | ML workloads, EKS nodes, Lambda functions |
| Isolated | PRIVATE_ISOLATED | None | Databases, caches, sensitive data stores |

### VPC Endpoints

When enabled, the following VPC endpoints are created to allow private connectivity to AWS services without traversing the internet:

**Gateway Endpoints (no cost):**
- Amazon S3
- Amazon DynamoDB

**Interface Endpoints:**
- SageMaker API and Runtime
- Bedrock and Bedrock Runtime
- ECR API and Docker
- CloudWatch Logs
- Systems Manager (SSM)
- Security Token Service (STS)
- Key Management Service (KMS)
- Secrets Manager

## Prerequisites

- AWS account with appropriate permissions
- [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting-started.html) installed
- Python 3.11 or later
- GitHub Actions OIDC provider configured in the target AWS account
- IAM role `GitHubActionsDeployRole` with trust policy for this repository

## Deployment

### Automatic Deployment

Push to the `main` branch to trigger automatic deployment via GitHub Actions.

### Manual Deployment

Trigger the **Deploy VPC Infrastructure** workflow manually from the GitHub Actions tab, selecting the target environment.

### Local Development

```bash
cd cdk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk synth
cdk diff
cdk deploy
```

## Destroy

Trigger the **Destroy VPC Infrastructure** workflow manually from the GitHub Actions tab. You must type `destroy` in the confirmation field.

## Configuration

| Parameter | Value |
|-----------|-------|
| Component Name | ${{ values.name }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.accountId }} |
| Environment | ${{ values.environment }} |
| VPC CIDR | ${{ values.vpcCidr }} |
| Availability Zones | ${{ values.availabilityZones }} |
| NAT Gateway | ${{ values.enableNatGateway }} |
| Single NAT Gateway | ${{ values.singleNatGateway }} |
| VPC Endpoints | ${{ values.enableVpcEndpoints }} |

## Outputs

After deployment, the following CloudFormation outputs are available:

| Output | Description |
|--------|-------------|
| `VpcId` | The VPC ID |
| `VpcCidr` | The VPC CIDR block |
| `PublicSubnetIds` | Comma-separated list of public subnet IDs |
| `PrivateSubnetIds` | Comma-separated list of private subnet IDs |
| `IsolatedSubnetIds` | Comma-separated list of isolated subnet IDs |
| `VpcEndpoints` | List of VPC interface endpoint names created |
| `VpcEndpointSecurityGroupId` | Security group ID for VPC endpoints |

## Using This VPC with Other GenForge Templates

When creating other GenForge components (RAG pipelines, SageMaker endpoints, EKS clusters), reference the exported VPC ID and subnet IDs from this stack.

## Owner

${{ values.owner }}

---

*Provisioned by [GenForge](https://github.com/your-org/genforge) - Forging GenAI infrastructure at scale*
