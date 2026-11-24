#!/bin/bash
# ==========================================================================
# GenForge Security Scan Runner
# ==========================================================================
# Runs all security checks and generates a consolidated HTML report.
#
# Usage:
#   ./scripts/security/run-security-scan.sh
#
# The scan performs five checks:
#   1. Secret detection (leaked credentials, tokens, keys)
#   2. Dependency audit (yarn packages and Python CDK dependencies)
#   3. CDK stack security review (encryption, IAM, tagging, removal policies)
#   4. GitHub Actions workflow review (pinned versions, OIDC, permissions)
#   5. HTML report generation
#
# Exit code:
#   0 - No critical or high-severity issues found
#   1 - Critical or high-severity issues detected
# ==========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$REPORT_DIR"

echo "=========================================="
echo "  GenForge Security Scan"
echo "  $(date)"
echo "=========================================="
echo ""

# Global counters — each sourced script increments these.
TOTAL_ISSUES=0
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

# Collector arrays for the report generator.
# Each entry is a pipe-delimited string: severity|category|file|line|description
declare -a FINDINGS=()

# Helper: record a finding and bump the appropriate counter.
record_finding() {
  local severity="$1"   # CRITICAL, HIGH, MEDIUM, LOW
  local category="$2"   # e.g. secrets, dependencies, cdk, actions
  local file="$3"       # file path (may be empty)
  local line="$4"       # line number (may be empty)
  local description="$5"

  FINDINGS+=("${severity}|${category}|${file}|${line}|${description}")
  ((TOTAL_ISSUES++)) || true

  case "$severity" in
    CRITICAL) ((CRITICAL_ISSUES++)) || true ;;
    HIGH)     ((HIGH_ISSUES++))     || true ;;
    MEDIUM)   ((MEDIUM_ISSUES++))   || true ;;
    LOW)      ((LOW_ISSUES++))      || true ;;
  esac
}

# ---------------------------------------------------------------------- #
# Run each check
# ---------------------------------------------------------------------- #

echo "[1/5] Checking for secrets..."
source "$SCRIPT_DIR/check-secrets.sh"
echo ""

echo "[2/5] Auditing dependencies..."
source "$SCRIPT_DIR/audit-dependencies.sh"
echo ""

echo "[3/5] Reviewing CDK stacks..."
source "$SCRIPT_DIR/review-cdk-stacks.sh"
echo ""

echo "[4/5] Reviewing GitHub Actions..."
source "$SCRIPT_DIR/review-github-actions.sh"
echo ""

echo "[5/5] Generating report..."
source "$SCRIPT_DIR/generate-report.sh"
echo ""

# ---------------------------------------------------------------------- #
# Summary
# ---------------------------------------------------------------------- #

echo "=========================================="
echo "  Scan Complete"
echo "  Total Issues:  $TOTAL_ISSUES"
echo "  Critical:      $CRITICAL_ISSUES"
echo "  High:          $HIGH_ISSUES"
echo "  Medium:        $MEDIUM_ISSUES"
echo "  Low:           $LOW_ISSUES"
echo "  Report:        $REPORT_DIR/security-report.html"
echo "=========================================="

# Exit with error if critical or high issues found.
if [ "$CRITICAL_ISSUES" -gt 0 ] || [ "$HIGH_ISSUES" -gt 0 ]; then
  exit 1
fi
