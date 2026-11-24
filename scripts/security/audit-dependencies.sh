#!/bin/bash
# ==========================================================================
# GenForge Dependency Audit
# ==========================================================================
# Audits JavaScript (Yarn) and Python (CDK) dependencies for known
# vulnerabilities, outdated packages, and version pinning issues.
#
# Designed to be sourced by run-security-scan.sh (uses record_finding,
# PROJECT_ROOT, and counter variables from the parent script).
# ==========================================================================

echo "  Auditing project dependencies..."

# ---------------------------------------------------------------------- #
# 1. JavaScript / Yarn audit
# ---------------------------------------------------------------------- #

echo ""
echo "  --- JavaScript Dependencies (Yarn) ---"

if command -v yarn &>/dev/null && [ -f "$PROJECT_ROOT/yarn.lock" ]; then
  # yarn npm audit returns exit code based on severity found.
  YARN_AUDIT_OUTPUT=""
  YARN_AUDIT_EXIT=0
  YARN_AUDIT_OUTPUT=$(cd "$PROJECT_ROOT" && yarn npm audit --all 2>&1) || YARN_AUDIT_EXIT=$?

  if [ "$YARN_AUDIT_EXIT" -eq 0 ]; then
    echo "  Yarn audit: No known vulnerabilities found."
  else
    # Count vulnerabilities by severity from the output.
    critical_count=$(echo "$YARN_AUDIT_OUTPUT" | grep -ci "critical" || true)
    high_count=$(echo "$YARN_AUDIT_OUTPUT" | grep -ci "high" || true)
    moderate_count=$(echo "$YARN_AUDIT_OUTPUT" | grep -ci "moderate" || true)
    low_count=$(echo "$YARN_AUDIT_OUTPUT" | grep -ci "low" || true)

    echo "  Yarn audit found vulnerabilities (exit code $YARN_AUDIT_EXIT):"
    echo "$YARN_AUDIT_OUTPUT" | tail -20

    if [ "$critical_count" -gt 0 ]; then
      record_finding "CRITICAL" "dependencies" "yarn.lock" "" \
        "Yarn audit found critical vulnerabilities ($critical_count references)"
    fi
    if [ "$high_count" -gt 0 ]; then
      record_finding "HIGH" "dependencies" "yarn.lock" "" \
        "Yarn audit found high-severity vulnerabilities ($high_count references)"
    fi
    if [ "$moderate_count" -gt 0 ]; then
      record_finding "MEDIUM" "dependencies" "yarn.lock" "" \
        "Yarn audit found moderate vulnerabilities ($moderate_count references)"
    fi
    if [ "$low_count" -gt 0 ]; then
      record_finding "LOW" "dependencies" "yarn.lock" "" \
        "Yarn audit found low-severity vulnerabilities ($low_count references)"
    fi
  fi
else
  echo "  Skipped: yarn not available or yarn.lock not found."
fi

# ---------------------------------------------------------------------- #
# 2. Python CDK dependencies audit
# ---------------------------------------------------------------------- #

echo ""
echo "  --- Python CDK Dependencies ---"

# Minimum acceptable versions for critical packages.
MIN_CDK_VERSION="2.170.0"
MIN_CONSTRUCTS_VERSION="10.0.0"
MIN_BOTO3_VERSION="1.34.0"

# Helper: compare two semver strings. Returns 0 if $1 >= $2.
version_gte() {
  local v1="$1"
  local v2="$2"
  # Use sort -V for version comparison.
  [ "$(printf '%s\n%s' "$v1" "$v2" | sort -V | head -n1)" = "$v2" ]
}

# Find all CDK requirements.txt files in the templates directory.
req_files_found=0
while IFS= read -r req_file; do
  ((req_files_found++)) || true
  display_path="${req_file#"$PROJECT_ROOT"/}"
  echo ""
  echo "  Checking: $display_path"

  # Parse each requirement line.
  while IFS= read -r line; do
    # Skip empty lines and comments.
    [[ -z "$line" || "$line" == \#* ]] && continue

    # Extract package name and version spec.
    pkg_name=$(echo "$line" | sed -E 's/([a-zA-Z0-9_-]+).*/\1/' | tr '[:upper:]' '[:lower:]')
    version_spec=$(echo "$line" | sed -E 's/[a-zA-Z0-9_-]+//')

    case "$pkg_name" in
      aws-cdk-lib)
        version=$(echo "$version_spec" | sed -E 's/[><=!]+//')
        if [ -n "$version" ]; then
          if ! version_gte "$version" "$MIN_CDK_VERSION"; then
            echo "    [HIGH] aws-cdk-lib version $version is below minimum $MIN_CDK_VERSION"
            record_finding "HIGH" "dependencies" "$display_path" "" \
              "aws-cdk-lib version $version is below recommended minimum $MIN_CDK_VERSION"
          else
            echo "    aws-cdk-lib: $version_spec (OK)"
          fi
        fi
        ;;
      constructs)
        version=$(echo "$version_spec" | sed -E 's/[><=!]+//')
        if [ -n "$version" ]; then
          if ! version_gte "$version" "$MIN_CONSTRUCTS_VERSION"; then
            echo "    [MEDIUM] constructs version $version is below minimum $MIN_CONSTRUCTS_VERSION"
            record_finding "MEDIUM" "dependencies" "$display_path" "" \
              "constructs version $version is below recommended minimum $MIN_CONSTRUCTS_VERSION"
          else
            echo "    constructs: $version_spec (OK)"
          fi
        fi
        ;;
      boto3)
        version=$(echo "$version_spec" | sed -E 's/[><=!]+//')
        if [ -n "$version" ]; then
          if ! version_gte "$version" "$MIN_BOTO3_VERSION"; then
            echo "    [MEDIUM] boto3 version $version is below minimum $MIN_BOTO3_VERSION"
            record_finding "MEDIUM" "dependencies" "$display_path" "" \
              "boto3 version $version is below recommended minimum $MIN_BOTO3_VERSION"
          else
            echo "    boto3: $version_spec (OK)"
          fi
        fi
        ;;
      *)
        echo "    $pkg_name: $version_spec"
        ;;
    esac
  done < "$req_file"

  # Check for unpinned dependencies (using >= without upper bound).
  unpinned=$(grep -cE '>=.*[^<]$' "$req_file" 2>/dev/null || true)
  if [ "$unpinned" -gt 0 ]; then
    echo "    [LOW] $unpinned package(s) use >= without an upper bound (unpinned)"
    record_finding "LOW" "dependencies" "$display_path" "" \
      "$unpinned package(s) use >= without an upper bound — consider pinning with < for reproducible builds"
  fi

done < <(find "$PROJECT_ROOT/templates" -name "requirements.txt" -path "*/cdk/*" 2>/dev/null)

if [ "$req_files_found" -eq 0 ]; then
  echo "  No CDK requirements.txt files found."
fi

# ---------------------------------------------------------------------- #
# 3. pip-audit (if available)
# ---------------------------------------------------------------------- #

echo ""
echo "  --- pip-audit (if available) ---"

if command -v pip-audit &>/dev/null; then
  while IFS= read -r req_file; do
    display_path="${req_file#"$PROJECT_ROOT"/}"
    echo "  Running pip-audit on: $display_path"

    audit_output=""
    audit_exit=0
    audit_output=$(pip-audit -r "$req_file" 2>&1) || audit_exit=$?

    if [ "$audit_exit" -eq 0 ]; then
      echo "    No known vulnerabilities."
    else
      echo "    pip-audit found issues:"
      echo "$audit_output" | head -20
      record_finding "HIGH" "dependencies" "$display_path" "" \
        "pip-audit reported vulnerabilities — review output for details"
    fi
  done < <(find "$PROJECT_ROOT/templates" -name "requirements.txt" -path "*/cdk/*" 2>/dev/null)
else
  echo "  Skipped: pip-audit not installed (pip install pip-audit to enable)."
fi

# ---------------------------------------------------------------------- #
# 4. Check for lock files in CDK directories
# ---------------------------------------------------------------------- #

echo ""
echo "  --- Lock File Presence ---"

while IFS= read -r req_file; do
  cdk_dir=$(dirname "$req_file")
  display_dir="${cdk_dir#"$PROJECT_ROOT"/}"

  if [ ! -f "$cdk_dir/requirements.lock" ] && [ ! -f "$cdk_dir/Pipfile.lock" ] && \
     [ ! -f "$cdk_dir/poetry.lock" ]; then
    echo "  [LOW] No Python lock file in $display_dir (builds may not be reproducible)"
    record_finding "LOW" "dependencies" "$display_dir/requirements.txt" "" \
      "No Python lock file found — builds may not be reproducible across environments"
  fi
done < <(find "$PROJECT_ROOT/templates" -name "requirements.txt" -path "*/cdk/*" 2>/dev/null)

echo ""
echo "  Dependency audit complete."
