#!/bin/bash
# ==========================================================================
# GenForge Secret Detection
# ==========================================================================
# Scans the entire project tree for leaked credentials, tokens, API keys,
# and private key material.
#
# Designed to be sourced by run-security-scan.sh (uses record_finding,
# PROJECT_ROOT, and counter variables from the parent script).
# ==========================================================================

echo "  Scanning for hardcoded secrets and credentials..."

# Patterns to search for. Each entry is  regex|label|severity .
SECRET_PATTERNS=(
  'AKIA[0-9A-Z]{16}|AWS Access Key ID|CRITICAL'
  'aws_secret_access_key\s*=\s*["\x27][^$\{]|AWS Secret Access Key assignment|CRITICAL'
  'BEGIN RSA PRIVATE KEY|RSA Private Key|CRITICAL'
  'BEGIN OPENSSH PRIVATE KEY|OpenSSH Private Key|CRITICAL'
  'BEGIN EC2 PRIVATE KEY|EC2 Private Key|CRITICAL'
  'BEGIN DSA PRIVATE KEY|DSA Private Key|CRITICAL'
  'BEGIN PGP PRIVATE KEY|PGP Private Key|CRITICAL'
  'ghp_[a-zA-Z0-9]{36}|GitHub Personal Access Token|CRITICAL'
  'gho_[a-zA-Z0-9]{36}|GitHub OAuth Token|CRITICAL'
  'ghs_[a-zA-Z0-9]{36}|GitHub App Installation Token|CRITICAL'
  'ghr_[a-zA-Z0-9]{36}|GitHub Refresh Token|CRITICAL'
  'sk-[a-zA-Z0-9]{20,}|API Secret Key (OpenAI/Stripe-style)|HIGH'
  'password\s*[:=]\s*["\x27][^$\{\}<][^"\x27]{4,}|Hardcoded password value|HIGH'
  'secret\s*[:=]\s*["\x27][^$\{\}<][^"\x27]{8,}|Hardcoded secret value|HIGH'
  'api[_-]?key\s*[:=]\s*["\x27][^$\{\}<][^"\x27]{8,}|Hardcoded API key|HIGH'
  'token\s*[:=]\s*["\x27][^$\{\}<][^"\x27]{8,}|Hardcoded token value|MEDIUM'
  'jdbc:.*password=|JDBC connection string with password|HIGH'
  'mongodb(\+srv)?://[^:]+:[^@]+@|MongoDB connection string with credentials|HIGH'
  'postgres://[^:]+:[^@]+@|PostgreSQL connection string with credentials|HIGH'
  'mysql://[^:]+:[^@]+@|MySQL connection string with credentials|HIGH'
)

# Patterns that indicate false positives. Lines matching any of these are skipped.
EXCLUDE_PATTERNS=(
  '\$\{.*\}'             # Environment variable references ${VAR}
  '\$\{\{.*\}\}'         # GitHub Actions expression ${{ ... }}
  'example\.com'         # Example domains
  'placeholder'          # Placeholder text
  '<YOUR_'               # User placeholder markers
  'CHANGE_ME'            # Placeholder markers
  'xxx'                  # Redacted values
  'TODO'                 # Notes to self
  'FIXME'                # Notes to self
  'os\.environ'          # Python env var references
  'process\.env'         # Node env var references
  'getenv'               # C/Python env var references
  'Values\.'             # Backstage scaffolder template values
  'values\.'             # Backstage scaffolder template values
  'context\.'            # CDK context references
  'ssm\.StringParameter'       # SSM parameter references
  'secretsmanager'             # Secrets Manager references
  'SecretsManager'             # Secrets Manager references
  'aws-cdk-lib'               # CDK dependency lines
  '\.md$'                      # Markdown documentation
  'CLAUDE\.md'                 # This project's guidance file
)

# Directories and files to skip entirely.
EXCLUDE_DIRS=(
  "node_modules"
  ".yarn"
  ".git"
  ".cache"
  "dist"
  "build"
  "__pycache__"
  ".pnp"
)

EXCLUDE_FILES=(
  "yarn.lock"
  "package-lock.json"
  "*.png"
  "*.jpg"
  "*.jpeg"
  "*.gif"
  "*.ico"
  "*.woff"
  "*.woff2"
  "*.ttf"
  "*.eot"
  "*.map"
  "*.min.js"
  "*.min.css"
)

# Build the find exclusion arguments.
FIND_EXCLUDES=()
for dir in "${EXCLUDE_DIRS[@]}"; do
  FIND_EXCLUDES+=(-path "*/$dir" -prune -o)
done

secrets_found=0

for pattern_entry in "${SECRET_PATTERNS[@]}"; do
  IFS='|' read -r pattern label severity <<< "$pattern_entry"

  # Use find + grep to search, excluding binary and irrelevant paths.
  while IFS= read -r match_line; do
    # Skip empty lines.
    [ -z "$match_line" ] && continue

    # Extract file path and line number from grep output (file:line:content).
    file_path="${match_line%%:*}"
    remainder="${match_line#*:}"
    line_number="${remainder%%:*}"
    line_content="${remainder#*:}"

    # Check if this is a known false positive.
    is_false_positive=false
    for exclude in "${EXCLUDE_PATTERNS[@]}"; do
      if echo "$line_content" | grep -qiE "$exclude" 2>/dev/null; then
        is_false_positive=true
        break
      fi
    done

    # Also skip the security scanning scripts themselves.
    if echo "$file_path" | grep -q "scripts/security/" 2>/dev/null; then
      is_false_positive=true
    fi

    # Skip excluded file types.
    for excl_file in "${EXCLUDE_FILES[@]}"; do
      if [[ "$file_path" == *"$excl_file"* ]] || [[ "$(basename "$file_path")" == $excl_file ]]; then
        is_false_positive=true
        break
      fi
    done

    if [ "$is_false_positive" = true ]; then
      continue
    fi

    # Strip PROJECT_ROOT prefix for cleaner display.
    display_path="${file_path#"$PROJECT_ROOT"/}"

    echo "  [$severity] $label"
    echo "    File: $display_path:$line_number"
    echo "    Content: $(echo "$line_content" | head -c 120)"
    echo ""

    record_finding "$severity" "secrets" "$display_path" "$line_number" "$label"
    ((secrets_found++)) || true

  done < <(find "$PROJECT_ROOT" "${FIND_EXCLUDES[@]}" -type f -print0 2>/dev/null | \
    xargs -0 grep -nEi "$pattern" 2>/dev/null || true)
done

if [ "$secrets_found" -eq 0 ]; then
  echo "  No hardcoded secrets detected."
else
  echo "  Found $secrets_found potential secret(s)."
fi
