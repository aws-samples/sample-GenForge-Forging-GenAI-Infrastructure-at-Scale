#!/bin/bash
# ==========================================================================
# GenForge CDK Stack Security Review
# ==========================================================================
# Reviews all CDK Python stacks for security best practices:
#   - Encryption at rest (SSE-KMS) on S3, databases, and other data stores
#   - S3 public access blocking and SSL enforcement
#   - IAM least-privilege (detects overly broad Resource: "*" + Action: "*")
#   - Removal policy correctness (dev=DESTROY, prod=RETAIN)
#   - Resource tagging (genforge:managed=true)
#   - VPC flow logs and restricted default security groups
#   - Logging configuration
#
# Designed to be sourced by run-security-scan.sh (uses record_finding,
# PROJECT_ROOT, and counter variables from the parent script).
# ==========================================================================

echo "  Reviewing CDK stack security posture..."
echo ""

stacks_reviewed=0
stacks_passed=0

# Find all CDK stack.py files.
while IFS= read -r stack_file; do
  ((stacks_reviewed++)) || true
  display_path="${stack_file#"$PROJECT_ROOT"/}"
  issues_in_stack=0

  echo "  Reviewing: $display_path"

  # Read the stack file content once.
  stack_content=$(cat "$stack_file")

  # ------------------------------------------------------------------ #
  # 1. Encryption at rest
  # ------------------------------------------------------------------ #

  # Check if any encryption-related constructs are present.
  if ! echo "$stack_content" | grep -qiE "encryption|SSE_KMS|encrypted|kms\.Key|EncryptionKey|server_side_encryption|encrypt"; then
    echo "    [HIGH] No encryption at rest configuration detected"
    record_finding "HIGH" "cdk" "$display_path" "" \
      "No encryption at rest configuration found — all data stores should use SSE-KMS"
    ((issues_in_stack++)) || true
  fi

  # Check for KMS key rotation.
  if echo "$stack_content" | grep -q "kms\.Key" && \
     ! echo "$stack_content" | grep -q "enable_key_rotation=True"; then
    echo "    [HIGH] KMS key created without key rotation enabled"
    record_finding "HIGH" "cdk" "$display_path" "" \
      "KMS key does not have enable_key_rotation=True — violates key management best practices"
    ((issues_in_stack++)) || true
  fi

  # ------------------------------------------------------------------ #
  # 2. S3 bucket security
  # ------------------------------------------------------------------ #

  if echo "$stack_content" | grep -qE "s3\.|Bucket\("; then
    # Block public access.
    if ! echo "$stack_content" | grep -qE "block_public_access|BlockPublicAccess"; then
      echo "    [HIGH] S3 bucket may not block public access"
      record_finding "HIGH" "cdk" "$display_path" "" \
        "S3 bucket missing block_public_access=BLOCK_ALL setting"
      ((issues_in_stack++)) || true
    fi

    # Enforce SSL (require HTTPS).
    if ! echo "$stack_content" | grep -qE "enforce_ssl|require_ssl"; then
      echo "    [MEDIUM] S3 bucket may not enforce SSL/TLS"
      record_finding "MEDIUM" "cdk" "$display_path" "" \
        "S3 bucket missing enforce_ssl=True — data in transit should require TLS"
      ((issues_in_stack++)) || true
    fi

    # Versioning.
    if ! echo "$stack_content" | grep -qE "versioned=True|versioning"; then
      echo "    [LOW] S3 bucket versioning not explicitly enabled"
      record_finding "LOW" "cdk" "$display_path" "" \
        "S3 bucket versioning not detected — enable for data protection and recovery"
      ((issues_in_stack++)) || true
    fi

    # Bucket encryption type.
    if echo "$stack_content" | grep -qE "BucketEncryption\.S3_MANAGED|BucketEncryption\.UNENCRYPTED"; then
      echo "    [MEDIUM] S3 bucket uses S3-managed or no encryption instead of KMS"
      record_finding "MEDIUM" "cdk" "$display_path" "" \
        "S3 bucket should use BucketEncryption.KMS for customer-managed encryption keys"
      ((issues_in_stack++)) || true
    fi
  fi

  # ------------------------------------------------------------------ #
  # 3. IAM least-privilege
  # ------------------------------------------------------------------ #

  # Detect overly permissive policies: actions=["*"] with resources=["*"].
  if echo "$stack_content" | grep -qE 'actions=\["\*"\]'; then
    # Find the line number for reporting.
    line_num=$(echo "$stack_content" | grep -nE 'actions=\["\*"\]' | head -1 | cut -d: -f1)
    echo "    [CRITICAL] Overly permissive IAM policy: actions=[\"*\"]"
    record_finding "CRITICAL" "cdk" "$display_path" "$line_num" \
      "IAM policy uses actions=[\"*\"] — violates least-privilege principle"
    ((issues_in_stack++)) || true
  fi

  # Detect wide resources with specific but broad action sets.
  if echo "$stack_content" | grep -qE 'resources=\["\*"\]'; then
    # Count how many times resources=["*"] appears.
    resource_star_count=$(echo "$stack_content" | grep -cE 'resources=\["\*"\]' || true)
    if [ "$resource_star_count" -gt 0 ]; then
      echo "    [MEDIUM] IAM policy uses resources=[\"*\"] ($resource_star_count occurrence(s))"
      record_finding "MEDIUM" "cdk" "$display_path" "" \
        "IAM policy uses resources=[\"*\"] $resource_star_count time(s) — scope resources where possible"
      ((issues_in_stack++)) || true
    fi
  fi

  # Check for AdministratorAccess managed policy.
  if echo "$stack_content" | grep -qiE "AdministratorAccess|PowerUserAccess"; then
    echo "    [CRITICAL] Stack references AdministratorAccess or PowerUserAccess managed policy"
    record_finding "CRITICAL" "cdk" "$display_path" "" \
      "Managed policy AdministratorAccess/PowerUserAccess detected — use least-privilege policies"
    ((issues_in_stack++)) || true
  fi

  # Check for iam:PassRole with resources=["*"].
  if echo "$stack_content" | grep -qE "iam:PassRole" && \
     echo "$stack_content" | grep -qE 'resources=\["\*"\]'; then
    echo "    [MEDIUM] iam:PassRole with resources=[\"*\"] — scope to specific role ARNs"
    record_finding "MEDIUM" "cdk" "$display_path" "" \
      "iam:PassRole granted on all resources — scope to specific role ARNs"
    ((issues_in_stack++)) || true
  fi

  # ------------------------------------------------------------------ #
  # 4. Removal policy
  # ------------------------------------------------------------------ #

  if ! echo "$stack_content" | grep -qE "RemovalPolicy|removal_policy"; then
    echo "    [MEDIUM] No removal policy configured — resources may be retained unexpectedly"
    record_finding "MEDIUM" "cdk" "$display_path" "" \
      "No RemovalPolicy configured — dev environments should use DESTROY, prod should use RETAIN"
    ((issues_in_stack++)) || true
  fi

  # Check for correct conditional pattern: dev=DESTROY, prod=RETAIN.
  if echo "$stack_content" | grep -qE "RemovalPolicy\.DESTROY"; then
    # Verify there is a conditional check (environment-based).
    if ! echo "$stack_content" | grep -qE 'environment.*==.*"dev"|environment.*dev.*DESTROY|removal.*=.*DESTROY.*if.*dev'; then
      # Check for the common pattern: removal = RemovalPolicy.DESTROY if environment == "dev" else RETAIN
      if ! echo "$stack_content" | grep -qE 'if.*environment.*==.*"dev".*else.*RETAIN|DESTROY.*if.*==.*"dev"'; then
        echo "    [LOW] DESTROY removal policy may not be conditioned on dev environment"
        record_finding "LOW" "cdk" "$display_path" "" \
          "RemovalPolicy.DESTROY found but not clearly conditioned on dev environment"
        ((issues_in_stack++)) || true
      fi
    fi
  fi

  # ------------------------------------------------------------------ #
  # 5. Resource tagging
  # ------------------------------------------------------------------ #

  if ! echo "$stack_content" | grep -qE 'genforge:managed|genforge.*managed.*true'; then
    echo "    [MEDIUM] Missing genforge:managed=true tag"
    record_finding "MEDIUM" "cdk" "$display_path" "" \
      "Stack missing genforge:managed=true tag — required for resource tracking and governance"
    ((issues_in_stack++)) || true
  fi

  if ! echo "$stack_content" | grep -qE 'Tags\.of\(self\)\.add\("environment"'; then
    echo "    [LOW] Missing environment tag"
    record_finding "LOW" "cdk" "$display_path" "" \
      "Stack missing environment tag on resources"
    ((issues_in_stack++)) || true
  fi

  if ! echo "$stack_content" | grep -qE 'Tags\.of\(self\)\.add\("owner"'; then
    echo "    [LOW] Missing owner tag"
    record_finding "LOW" "cdk" "$display_path" "" \
      "Stack missing owner tag on resources"
    ((issues_in_stack++)) || true
  fi

  # ------------------------------------------------------------------ #
  # 6. VPC and networking (only for stacks that use VPC)
  # ------------------------------------------------------------------ #

  if echo "$stack_content" | grep -qE "ec2\.Vpc|aws_ec2"; then
    # VPC flow logs.
    if echo "$stack_content" | grep -qE "Vpc\(" && \
       ! echo "$stack_content" | grep -qiE "flow_log|FlowLog|add_flow_log"; then
      echo "    [MEDIUM] VPC created without flow logs"
      record_finding "MEDIUM" "cdk" "$display_path" "" \
        "VPC does not have flow logs enabled — required for network traffic monitoring"
      ((issues_in_stack++)) || true
    fi

    # Default security group restriction.
    if echo "$stack_content" | grep -qE "Vpc\(" && \
       ! echo "$stack_content" | grep -qiE "restrict_default_security_group|default_security_group"; then
      # This is informational; CDK v2 restricts by default, but explicit is better.
      echo "    [LOW] VPC does not explicitly restrict default security group"
      record_finding "LOW" "cdk" "$display_path" "" \
        "Consider explicitly setting restrict_default_security_group=True on VPC"
      ((issues_in_stack++)) || true
    fi
  fi

  # ------------------------------------------------------------------ #
  # 7. Logging
  # ------------------------------------------------------------------ #

  # Check that Lambda functions have associated log groups.
  if echo "$stack_content" | grep -qE "lambda_\.Function|lambda\.Function"; then
    if ! echo "$stack_content" | grep -qE "logs\.LogGroup|log_group|LogGroup"; then
      echo "    [LOW] Lambda function(s) without explicit CloudWatch log group configuration"
      record_finding "LOW" "cdk" "$display_path" "" \
        "Lambda functions should have explicit log group with retention and removal policy"
      ((issues_in_stack++)) || true
    fi
  fi

  # ------------------------------------------------------------------ #
  # 8. Secrets in CDK code
  # ------------------------------------------------------------------ #

  # Check for hardcoded ARNs with account IDs (not using self.account).
  if echo "$stack_content" | grep -qE 'arn:aws:[a-z]+:[a-z0-9-]*:[0-9]{12}:'; then
    line_num=$(echo "$stack_content" | grep -nE 'arn:aws:[a-z]+:[a-z0-9-]*:[0-9]{12}:' | head -1 | cut -d: -f1)
    echo "    [MEDIUM] Hardcoded AWS account ID in ARN"
    record_finding "MEDIUM" "cdk" "$display_path" "$line_num" \
      "Hardcoded AWS account ID in ARN — use self.account or Fn.ref for portability"
    ((issues_in_stack++)) || true
  fi

  # ------------------------------------------------------------------ #
  # Summary for this stack
  # ------------------------------------------------------------------ #

  if [ "$issues_in_stack" -eq 0 ]; then
    echo "    All checks passed."
    ((stacks_passed++)) || true
  else
    echo "    $issues_in_stack issue(s) found."
  fi
  echo ""

done < <(find "$PROJECT_ROOT/templates" -name "stack.py" -path "*/cdk/*" 2>/dev/null)

echo "  CDK review complete: $stacks_reviewed stack(s) reviewed, $stacks_passed fully passed."
