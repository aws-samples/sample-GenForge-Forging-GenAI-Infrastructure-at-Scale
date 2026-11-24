#!/bin/bash
# One-time setup script to create GitHub OIDC provider and IAM role
# Run this locally with your AWS credentials exported
#
# Usage: ./setup-github-oidc.sh <github-org> <aws-account-id> <aws-region>
# Example: ./setup-github-oidc.sh hmshashank 123456789012 us-west-2

set -e

# Configuration from arguments or environment
GITHUB_ORG="${1}"
AWS_ACCOUNT_ID="${2:-${AWS_ACCOUNT_ID}}"
AWS_REGION="${3:-${AWS_REGION:-us-west-2}}"

if [ -z "$GITHUB_ORG" ]; then
    echo "❌ ERROR: GitHub organization not provided"
    echo ""
    echo "Usage: $0 <github-org> [aws-account-id] [aws-region]"
    echo "Example: $0 hmshashank 123456789012 us-west-2"
    echo ""
    echo "Or set environment variables:"
    echo "  export AWS_ACCOUNT_ID=123456789012"
    echo "  export AWS_REGION=us-west-2"
    echo "  $0 hmshashank"
    exit 1
fi

echo "=========================================="
echo "GitHub OIDC Setup for AWS"
echo "=========================================="
echo "AWS Account: ${AWS_ACCOUNT_ID}"
echo "AWS Region: ${AWS_REGION}"
echo "GitHub Org: ${GITHUB_ORG}"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ ERROR: AWS credentials not configured"
    echo ""
    echo "Please export your AWS credentials:"
    echo "  export AWS_ACCESS_KEY_ID=your-key"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret"
    exit 1
fi

echo "✅ AWS credentials verified"
echo ""

# Create OIDC Provider
echo "1️⃣  Creating GitHub OIDC Provider..."
if aws iam list-open-id-connect-providers | grep -q "token.actions.githubusercontent.com"; then
    echo "✅ GitHub OIDC provider already exists"
else
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd
    echo "✅ GitHub OIDC provider created"
fi
echo ""

# Get OIDC Provider ARN
OIDC_PROVIDER_ARN=$(aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text)
echo "OIDC Provider ARN: ${OIDC_PROVIDER_ARN}"
echo ""

# Create IAM Role
echo "2️⃣  Creating GitHubActionsDeployRole..."
if aws iam get-role --role-name GitHubActionsDeployRole > /dev/null 2>&1; then
    echo "✅ GitHubActionsDeployRole already exists"
    echo "Updating trust policy..."
else
    echo "Creating new role..."
fi

# Create trust policy (allows all repos in the org)
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/*:ref:refs/*"
        }
      }
    }
  ]
}
EOF

# Create or update role
if aws iam get-role --role-name GitHubActionsDeployRole > /dev/null 2>&1; then
    aws iam update-assume-role-policy \
        --role-name GitHubActionsDeployRole \
        --policy-document file:///tmp/trust-policy.json
    echo "✅ Trust policy updated"
else
    aws iam create-role \
        --role-name GitHubActionsDeployRole \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for GitHub Actions to deploy infrastructure" \
        --max-session-duration 3600
    echo "✅ Role created"
fi
echo ""

# Attach policies
echo "3️⃣  Attaching policies..."

# Detach the broad PowerUserAccess managed policy if it was attached by a
# previous run of this script. GenForge templates now use a scoped inline
# deploy policy instead (see CDKDeployPolicy below).
if aws iam list-attached-role-policies --role-name GitHubActionsDeployRole | grep -q "PowerUserAccess"; then
    aws iam detach-role-policy \
        --role-name GitHubActionsDeployRole \
        --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
    echo "✅ Removed legacy PowerUserAccess (replaced with scoped CDKDeployPolicy)"
fi

# Scoped inline CDK deploy policy.
# Grants only the services and actions the generated CDK stacks need to
# provision, all constrained to the target region. Adjust the action list
# if you extend a template with additional AWS services.
cat > /tmp/deploy-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CDKDeploy",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "ecs:*",
        "ecr:*",
        "eks:Describe*",
        "eks:List*",
        "ec2:Describe*",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroup*",
        "ec2:RevokeSecurityGroup*",
        "ec2:CreateTags",
        "logs:*",
        "cloudwatch:*",
        "kms:CreateKey",
        "kms:CreateAlias",
        "kms:DescribeKey",
        "kms:ListAliases",
        "kms:TagResource",
        "kms:UpdateAlias",
        "kms:PutKeyPolicy",
        "kms:EnableKeyRotation",
        "kms:ScheduleKeyDeletion",
        "elasticloadbalancing:*",
        "dynamodb:*",
        "bedrock:List*",
        "bedrock:Get*",
        "sagemaker:List*",
        "sagemaker:Describe*",
        "sagemaker:AddTags",
        "aoss:*",
        "cognito-idp:*",
        "states:*",
        "sns:*",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:PassRole",
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["${AWS_REGION}"]
        }
      }
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name GitHubActionsDeployRole \
    --policy-name CDKDeployPolicy \
    --policy-document file:///tmp/deploy-policy.json
echo "✅ Scoped CDKDeployPolicy attached (region-locked)"

# Scoped iam:PassRole policy. Only allows passing roles to the CDK/CFN
# execution services actually used by the generated stacks.
cat > /tmp/passrole-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "cloudformation.amazonaws.com",
            "lambda.amazonaws.com",
            "ecs-tasks.amazonaws.com",
            "sagemaker.amazonaws.com",
            "bedrock.amazonaws.com",
            "states.amazonaws.com"
          ]
        }
      }
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name GitHubActionsDeployRole \
    --policy-name IAMPassRolePolicy \
    --policy-document file:///tmp/passrole-policy.json
echo "✅ IAM PassRole policy attached (scoped to deploy-time service principals)"
echo ""

# Cleanup
rm -f /tmp/trust-policy.json /tmp/deploy-policy.json /tmp/passrole-policy.json

# Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Resources created:"
echo "  • GitHub OIDC Provider"
echo "  • IAM Role: GitHubActionsDeployRole"
echo "  • Trust policy: repo:${GITHUB_ORG}/*:ref:refs/*"
echo "  • Policies: CDKDeployPolicy (scoped, region-locked) + IAMPassRolePolicy"
echo ""
echo "All repositories in ${GITHUB_ORG} can now use OIDC!"
echo ""
echo "No AWS access keys needed in GitHub secrets."
echo "=========================================="
