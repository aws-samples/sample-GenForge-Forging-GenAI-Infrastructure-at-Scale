#!/bin/bash
# ==========================================================================
# GenForge Security Report Generator
# ==========================================================================
# Generates a professional HTML report from the findings collected by the
# other security scanning scripts.
#
# Designed to be sourced by run-security-scan.sh (uses FINDINGS array,
# REPORT_DIR, TIMESTAMP, and counter variables from the parent script).
# ==========================================================================

REPORT_FILE="$REPORT_DIR/security-report.html"

echo "  Generating HTML report: $REPORT_FILE"

# ---------------------------------------------------------------------- #
# Helper: count findings by category
# ---------------------------------------------------------------------- #

count_by_category() {
  local cat="$1"
  local count=0
  for finding in "${FINDINGS[@]:-}"; do
    if echo "$finding" | grep -q "|${cat}|"; then
      ((count++)) || true
    fi
  done
  echo "$count"
}

count_by_severity() {
  local sev="$1"
  local count=0
  for finding in "${FINDINGS[@]:-}"; do
    if echo "$finding" | grep -q "^${sev}|"; then
      ((count++)) || true
    fi
  done
  echo "$count"
}

# Count per category.
secrets_count=$(count_by_category "secrets")
dependencies_count=$(count_by_category "dependencies")
cdk_count=$(count_by_category "cdk")
actions_count=$(count_by_category "actions")

# Determine overall status.
if [ "$CRITICAL_ISSUES" -gt 0 ]; then
  overall_status="FAIL"
  overall_class="fail"
  overall_icon="&#10060;"
elif [ "$HIGH_ISSUES" -gt 0 ]; then
  overall_status="FAIL"
  overall_class="fail"
  overall_icon="&#10060;"
elif [ "$MEDIUM_ISSUES" -gt 0 ]; then
  overall_status="WARN"
  overall_class="warn"
  overall_icon="&#9888;&#65039;"
else
  overall_status="PASS"
  overall_class="pass"
  overall_icon="&#9989;"
fi

# ---------------------------------------------------------------------- #
# Generate HTML
# ---------------------------------------------------------------------- #

cat > "$REPORT_FILE" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GenForge Security Scan Report</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      margin: 40px;
      background: #f5f5f5;
      color: #333;
      line-height: 1.6;
    }
    .container {
      max-width: 1100px;
      margin: 0 auto;
      background: white;
      padding: 40px;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    h1 {
      color: #1a1a2e;
      border-bottom: 3px solid #e94560;
      padding-bottom: 12px;
      margin-bottom: 8px;
      font-size: 28px;
    }
    .subtitle {
      color: #666;
      font-size: 14px;
      margin-bottom: 24px;
    }
    h2 {
      color: #1a1a2e;
      margin-top: 32px;
      margin-bottom: 16px;
      font-size: 20px;
      border-bottom: 1px solid #eee;
      padding-bottom: 8px;
    }
    h3 {
      color: #444;
      margin-top: 20px;
      margin-bottom: 10px;
      font-size: 16px;
    }

    /* Summary cards */
    .summary {
      display: flex;
      gap: 16px;
      margin: 24px 0;
      flex-wrap: wrap;
    }
    .stat {
      padding: 20px;
      border-radius: 10px;
      flex: 1;
      min-width: 140px;
      text-align: center;
      transition: transform 0.2s;
    }
    .stat:hover { transform: translateY(-2px); }
    .stat .number { font-size: 36px; font-weight: 700; }
    .stat .label { font-size: 13px; font-weight: 500; margin-top: 4px; }
    .stat.pass { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .stat.fail { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .stat.warn { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .stat.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    .stat.neutral { background: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }

    /* Category overview */
    .categories {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 20px 0;
    }
    .category-card {
      padding: 16px;
      border-radius: 8px;
      background: #fafafa;
      border: 1px solid #eee;
    }
    .category-card .cat-name { font-weight: 600; font-size: 14px; color: #333; }
    .category-card .cat-count { font-size: 24px; font-weight: 700; margin-top: 4px; }
    .category-card.clean { border-left: 4px solid #28a745; }
    .category-card.issues { border-left: 4px solid #dc3545; }

    /* Findings table */
    .findings-table {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
      font-size: 14px;
    }
    .findings-table th {
      background: #1a1a2e;
      color: white;
      padding: 10px 14px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
    }
    .findings-table td {
      padding: 10px 14px;
      border-bottom: 1px solid #eee;
      vertical-align: top;
    }
    .findings-table tr:hover td { background: #f8f9fa; }
    .findings-table tr:nth-child(even) td { background: #fafafa; }
    .findings-table tr:nth-child(even):hover td { background: #f0f0f0; }

    /* Severity badges */
    .severity {
      display: inline-block;
      padding: 3px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .severity.critical { background: #dc3545; color: white; }
    .severity.high { background: #fd7e14; color: white; }
    .severity.medium { background: #ffc107; color: #333; }
    .severity.low { background: #28a745; color: white; }

    .file-path {
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 12px;
      color: #6c63ff;
      word-break: break-all;
    }

    .no-issues {
      text-align: center;
      padding: 40px;
      color: #28a745;
      font-size: 18px;
    }

    /* Footer */
    .footer {
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #eee;
      font-size: 12px;
      color: #888;
      text-align: center;
    }

    /* Overall status banner */
    .status-banner {
      padding: 16px 24px;
      border-radius: 8px;
      font-size: 18px;
      font-weight: 700;
      text-align: center;
      margin: 20px 0;
    }
    .status-banner.pass { background: #d4edda; color: #155724; border: 2px solid #28a745; }
    .status-banner.fail { background: #f8d7da; color: #721c24; border: 2px solid #dc3545; }
    .status-banner.warn { background: #fff3cd; color: #856404; border: 2px solid #ffc107; }

    @media (max-width: 768px) {
      body { margin: 16px; }
      .container { padding: 20px; }
      .summary { flex-direction: column; }
      .stat { min-width: auto; }
    }
  </style>
</head>
<body>
<div class="container">
HTMLHEAD

# Title and metadata.
cat >> "$REPORT_FILE" << EOF
  <h1>GenForge Security Scan Report</h1>
  <div class="subtitle">
    Generated: $(date '+%Y-%m-%d %H:%M:%S %Z') &nbsp;|&nbsp;
    Project: GenForge IDP &nbsp;|&nbsp;
    Scan ID: $TIMESTAMP
  </div>

  <!-- Overall Status -->
  <div class="status-banner $overall_class">
    $overall_icon &nbsp; Overall Status: $overall_status
  </div>

  <!-- Summary Statistics -->
  <h2>Summary</h2>
  <div class="summary">
    <div class="stat neutral">
      <div class="number">$TOTAL_ISSUES</div>
      <div class="label">Total Issues</div>
    </div>
    <div class="stat $([ "$CRITICAL_ISSUES" -gt 0 ] && echo 'fail' || echo 'pass')">
      <div class="number">$CRITICAL_ISSUES</div>
      <div class="label">Critical</div>
    </div>
    <div class="stat $([ "$HIGH_ISSUES" -gt 0 ] && echo 'fail' || echo 'pass')">
      <div class="number">$HIGH_ISSUES</div>
      <div class="label">High</div>
    </div>
    <div class="stat $([ "$MEDIUM_ISSUES" -gt 0 ] && echo 'warn' || echo 'pass')">
      <div class="number">$MEDIUM_ISSUES</div>
      <div class="label">Medium</div>
    </div>
    <div class="stat $([ "$LOW_ISSUES" -gt 0 ] && echo 'info' || echo 'pass')">
      <div class="number">$LOW_ISSUES</div>
      <div class="label">Low</div>
    </div>
  </div>

  <!-- Category Breakdown -->
  <h2>Category Breakdown</h2>
  <div class="categories">
    <div class="category-card $([ "$secrets_count" -gt 0 ] && echo 'issues' || echo 'clean')">
      <div class="cat-name">Secrets Detection</div>
      <div class="cat-count">$secrets_count</div>
    </div>
    <div class="category-card $([ "$dependencies_count" -gt 0 ] && echo 'issues' || echo 'clean')">
      <div class="cat-name">Dependency Audit</div>
      <div class="cat-count">$dependencies_count</div>
    </div>
    <div class="category-card $([ "$cdk_count" -gt 0 ] && echo 'issues' || echo 'clean')">
      <div class="cat-name">CDK Stack Review</div>
      <div class="cat-count">$cdk_count</div>
    </div>
    <div class="category-card $([ "$actions_count" -gt 0 ] && echo 'issues' || echo 'clean')">
      <div class="cat-name">GitHub Actions Review</div>
      <div class="cat-count">$actions_count</div>
    </div>
  </div>
EOF

# ---------------------------------------------------------------------- #
# Detailed Findings
# ---------------------------------------------------------------------- #

cat >> "$REPORT_FILE" << 'EOF'
  <h2>Detailed Findings</h2>
EOF

if [ "${#FINDINGS[@]}" -eq 0 ] 2>/dev/null || [ -z "${FINDINGS[0]:-}" ]; then
  cat >> "$REPORT_FILE" << 'EOF'
  <div class="no-issues">
    No security issues detected. All checks passed.
  </div>
EOF
else
  # Build findings table sorted by severity (CRITICAL first, then HIGH, MEDIUM, LOW).
  cat >> "$REPORT_FILE" << 'EOF'
  <table class="findings-table">
    <thead>
      <tr>
        <th style="width: 90px;">Severity</th>
        <th style="width: 120px;">Category</th>
        <th style="width: 260px;">Location</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
EOF

  # Sort findings: CRITICAL=1, HIGH=2, MEDIUM=3, LOW=4.
  sorted_findings=()
  for sev in CRITICAL HIGH MEDIUM LOW; do
    for finding in "${FINDINGS[@]}"; do
      if echo "$finding" | grep -q "^${sev}|"; then
        sorted_findings+=("$finding")
      fi
    done
  done

  for finding in "${sorted_findings[@]}"; do
    IFS='|' read -r severity category file line description <<< "$finding"

    # Map severity to CSS class.
    sev_class=$(echo "$severity" | tr '[:upper:]' '[:lower:]')

    # Build location string.
    location="$file"
    if [ -n "$line" ]; then
      location="${file}:${line}"
    fi

    # Map category to display name.
    case "$category" in
      secrets)      cat_display="Secrets" ;;
      dependencies) cat_display="Dependencies" ;;
      cdk)          cat_display="CDK Stack" ;;
      actions)      cat_display="GitHub Actions" ;;
      *)            cat_display="$category" ;;
    esac

    # Escape HTML special characters in description.
    safe_desc=$(echo "$description" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')
    safe_location=$(echo "$location" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g')

    cat >> "$REPORT_FILE" << EOF
      <tr>
        <td><span class="severity $sev_class">$severity</span></td>
        <td>$cat_display</td>
        <td><span class="file-path">$safe_location</span></td>
        <td>$safe_desc</td>
      </tr>
EOF
  done

  cat >> "$REPORT_FILE" << 'EOF'
    </tbody>
  </table>
EOF
fi

# ---------------------------------------------------------------------- #
# Per-Category Detail Sections
# ---------------------------------------------------------------------- #

# Secrets section.
cat >> "$REPORT_FILE" << EOF
  <h2>1. Secrets Detection</h2>
EOF
if [ "$secrets_count" -eq 0 ]; then
  cat >> "$REPORT_FILE" << 'EOF'
  <p style="color: #28a745; font-weight: 600;">No hardcoded secrets or credentials detected.</p>
  <p>The scan checked for: AWS access keys, private keys (RSA/SSH/EC2/DSA/PGP), GitHub tokens,
  API secret keys, hardcoded passwords, and database connection strings with embedded credentials.</p>
EOF
else
  cat >> "$REPORT_FILE" << EOF
  <p style="color: #dc3545; font-weight: 600;">$secrets_count potential secret(s) detected.</p>
  <p>Review each finding above and either remove the secret, rotate it if exposed, or
  move it to a secrets manager (AWS Secrets Manager, SSM Parameter Store, or GitHub Actions secrets).</p>
EOF
fi

# Dependencies section.
cat >> "$REPORT_FILE" << EOF
  <h2>2. Dependency Audit</h2>
EOF
if [ "$dependencies_count" -eq 0 ]; then
  cat >> "$REPORT_FILE" << 'EOF'
  <p style="color: #28a745; font-weight: 600;">No dependency vulnerabilities or version issues found.</p>
EOF
else
  cat >> "$REPORT_FILE" << EOF
  <p>$dependencies_count dependency issue(s) found. Review package versions and run
  <code>yarn npm audit</code> and <code>pip-audit</code> for detailed vulnerability information.</p>
EOF
fi

# CDK section.
cat >> "$REPORT_FILE" << EOF
  <h2>3. CDK Stack Security Review</h2>
  <h3>Checks Performed</h3>
  <ul>
    <li>Encryption at rest (SSE-KMS) and KMS key rotation</li>
    <li>S3 bucket public access blocking, SSL enforcement, versioning</li>
    <li>IAM least-privilege (no actions=["*"] or resources=["*"])</li>
    <li>Removal policy correctness (dev=DESTROY, prod=RETAIN)</li>
    <li>Resource tagging (genforge:managed, environment, owner)</li>
    <li>VPC flow logs and security group configuration</li>
    <li>CloudWatch log group configuration for Lambda functions</li>
    <li>Hardcoded AWS account IDs in ARNs</li>
  </ul>
EOF
if [ "$cdk_count" -eq 0 ]; then
  cat >> "$REPORT_FILE" << 'EOF'
  <p style="color: #28a745; font-weight: 600; margin-top: 12px;">All CDK stacks passed security review.</p>
EOF
else
  cat >> "$REPORT_FILE" << EOF
  <p style="margin-top: 12px;">$cdk_count CDK security issue(s) found. See the findings table above for details.</p>
EOF
fi

# GitHub Actions section.
cat >> "$REPORT_FILE" << EOF
  <h2>4. GitHub Actions Workflow Review</h2>
  <h3>Checks Performed</h3>
  <ul>
    <li>Action version pinning (must use @vN, not @main or floating tags)</li>
    <li>OIDC authentication (no long-lived AWS credentials)</li>
    <li>Minimal permissions (id-token: write, contents: read)</li>
    <li>Script injection risks (\${{ github.event.* }} in run: blocks)</li>
    <li>Dangerous flags (--require-approval never, --force)</li>
    <li>Workflow trigger security (pull_request_target caution)</li>
  </ul>
EOF
if [ "$actions_count" -eq 0 ]; then
  cat >> "$REPORT_FILE" << 'EOF'
  <p style="color: #28a745; font-weight: 600; margin-top: 12px;">All GitHub Actions workflows passed security review.</p>
EOF
else
  cat >> "$REPORT_FILE" << EOF
  <p style="margin-top: 12px;">$actions_count GitHub Actions issue(s) found. See the findings table above for details.</p>
EOF
fi

# ---------------------------------------------------------------------- #
# Recommendations
# ---------------------------------------------------------------------- #

cat >> "$REPORT_FILE" << 'EOF'
  <h2>Recommendations</h2>
  <ul>
    <li><strong>Secrets:</strong> Use AWS Secrets Manager or SSM Parameter Store for all credentials.
    Never commit secrets to source control. Rotate any credentials that may have been exposed.</li>
    <li><strong>Dependencies:</strong> Run <code>yarn npm audit</code> regularly. Pin Python CDK
    dependencies with upper bounds. Consider adding <code>pip-audit</code> to CI pipelines.</li>
    <li><strong>CDK Stacks:</strong> Ensure all data stores use SSE-KMS encryption, all S3 buckets
    block public access and enforce SSL, and all IAM policies follow least-privilege. Tag all
    resources with <code>genforge:managed=true</code>.</li>
    <li><strong>GitHub Actions:</strong> Pin all actions to specific version tags (@v4, not @main).
    Use OIDC for AWS authentication. Map secrets to environment variables rather than using them
    directly in <code>run:</code> blocks.</li>
    <li><strong>General:</strong> Integrate this security scan into CI/CD pipelines to catch
    issues before they reach production.</li>
  </ul>
EOF

# ---------------------------------------------------------------------- #
# Footer
# ---------------------------------------------------------------------- #

cat >> "$REPORT_FILE" << EOF
  <div class="footer">
    GenForge Security Scan &mdash; $(date '+%Y-%m-%d %H:%M:%S %Z') &mdash; Scan ID: $TIMESTAMP
    <br>
    Scanned $(find "$PROJECT_ROOT/templates" -name "stack.py" -path "*/cdk/*" 2>/dev/null | wc -l | tr -d ' ') CDK stack(s),
    $(find "$PROJECT_ROOT/templates" -name "*.yml" -path "*/.github/workflows/*" 2>/dev/null | wc -l | tr -d ' ') GitHub Actions workflow(s)
  </div>

</div>
</body>
</html>
EOF

echo "  Report generated: $REPORT_FILE"
