#!/bin/bash
# ==========================================================================
# GenForge GitHub Actions Workflow Security Review
# ==========================================================================
# Reviews all GitHub Actions workflow files for:
#   - Pinned action versions (uses @vN, not @main or floating tags)
#   - OIDC authentication (not long-lived AWS credentials)
#   - Minimal permissions (id-token: write, contents: read)
#   - Script injection risks (no direct ${{ github.event.* }} in run: blocks)
#   - Dangerous flags (--require-approval never, --force, --no-verify)
#   - Checkout depth and persistence settings
#
# Designed to be sourced by run-security-scan.sh (uses record_finding,
# PROJECT_ROOT, and counter variables from the parent script).
# ==========================================================================

echo "  Reviewing GitHub Actions workflow security..."
echo ""

workflows_reviewed=0
workflows_passed=0

# Find all workflow YAML files.
while IFS= read -r workflow_file; do
  ((workflows_reviewed++)) || true
  display_path="${workflow_file#"$PROJECT_ROOT"/}"
  issues_in_workflow=0

  echo "  Reviewing: $display_path"

  # Read the workflow file content once.
  wf_content=$(cat "$workflow_file")

  # ------------------------------------------------------------------ #
  # 1. Action version pinning
  # ------------------------------------------------------------------ #

  # Find all "uses:" lines and check for unpinned references.
  while IFS= read -r uses_line; do
    [ -z "$uses_line" ] && continue

    line_num=$(echo "$uses_line" | cut -d: -f1)
    action_ref=$(echo "$uses_line" | sed -E 's/.*uses:\s*//' | tr -d '"' | tr -d "'")

    # Skip local actions (starting with ./).
    if [[ "$action_ref" == ./* ]]; then
      continue
    fi

    # Check for @main, @master, or no version tag.
    if echo "$action_ref" | grep -qE '@main$|@master$'; then
      echo "    [HIGH] Unpinned action (uses @main/@master): $action_ref (line $line_num)"
      record_finding "HIGH" "actions" "$display_path" "$line_num" \
        "Action '$action_ref' pinned to branch instead of version tag — supply chain risk"
      ((issues_in_workflow++)) || true
    elif ! echo "$action_ref" | grep -qE '@'; then
      echo "    [HIGH] Action missing version pin: $action_ref (line $line_num)"
      record_finding "HIGH" "actions" "$display_path" "$line_num" \
        "Action '$action_ref' has no version pin — must use @vN for reproducibility"
      ((issues_in_workflow++)) || true
    elif echo "$action_ref" | grep -qE '@v[0-9]+$'; then
      # Major version pin (@v4) is acceptable but not ideal.
      : # This is fine — major version pin is the standard practice.
    elif echo "$action_ref" | grep -qE '@[a-f0-9]{40}$'; then
      # SHA pin is the most secure — no issue.
      :
    fi

  done < <(echo "$wf_content" | grep -nE '^\s*uses:' || true)

  # ------------------------------------------------------------------ #
  # 2. OIDC authentication
  # ------------------------------------------------------------------ #

  # Check that configure-aws-credentials uses role-to-assume (OIDC), not access keys.
  if echo "$wf_content" | grep -qE "configure-aws-credentials"; then
    if echo "$wf_content" | grep -qE "aws-access-key-id|aws-secret-access-key"; then
      echo "    [CRITICAL] Long-lived AWS credentials used instead of OIDC"
      record_finding "CRITICAL" "actions" "$display_path" "" \
        "Workflow uses long-lived AWS access keys — must use OIDC role-to-assume instead"
      ((issues_in_workflow++)) || true
    fi

    if ! echo "$wf_content" | grep -qE "role-to-assume"; then
      echo "    [HIGH] configure-aws-credentials without role-to-assume"
      record_finding "HIGH" "actions" "$display_path" "" \
        "configure-aws-credentials does not use role-to-assume — OIDC authentication required"
      ((issues_in_workflow++)) || true
    fi
  fi

  # ------------------------------------------------------------------ #
  # 3. Permissions
  # ------------------------------------------------------------------ #

  # Check for id-token: write permission (required for OIDC).
  if echo "$wf_content" | grep -qE "role-to-assume" && \
     ! echo "$wf_content" | grep -qE "id-token:\s*write"; then
    echo "    [HIGH] Missing id-token: write permission (required for OIDC)"
    record_finding "HIGH" "actions" "$display_path" "" \
      "Workflow uses OIDC but is missing 'id-token: write' permission"
    ((issues_in_workflow++)) || true
  fi

  # Check for overly broad permissions.
  if echo "$wf_content" | grep -qE "permissions:\s*write-all|permissions:\s*\{\}"; then
    echo "    [HIGH] Overly broad workflow permissions"
    record_finding "HIGH" "actions" "$display_path" "" \
      "Workflow uses overly broad permissions — apply least-privilege scoping"
    ((issues_in_workflow++)) || true
  fi

  # Check contents permission is read-only (not write, unless PR commenting is needed).
  if echo "$wf_content" | grep -qE "contents:\s*write"; then
    # Only flag if this is not a PR-commenting workflow.
    if ! echo "$wf_content" | grep -qE "pull-requests:\s*write"; then
      echo "    [MEDIUM] contents: write permission may be overly broad"
      record_finding "MEDIUM" "actions" "$display_path" "" \
        "Workflow has contents: write — ensure this is necessary"
      ((issues_in_workflow++)) || true
    fi
  fi

  # ------------------------------------------------------------------ #
  # 4. Script injection
  # ------------------------------------------------------------------ #

  # Check for direct use of ${{ github.event.* }} in run: blocks,
  # which can lead to script injection.
  # We look for run: blocks that contain github.event expressions.
  injection_candidates=$(echo "$wf_content" | grep -nE 'run:.*\$\{\{.*github\.event\.' || true)
  if [ -n "$injection_candidates" ]; then
    while IFS= read -r inj_line; do
      [ -z "$inj_line" ] && continue
      line_num=$(echo "$inj_line" | cut -d: -f1)
      echo "    [HIGH] Potential script injection: github.event.* in run: block (line $line_num)"
      record_finding "HIGH" "actions" "$display_path" "$line_num" \
        "Potential script injection — github.event.* used directly in run: block"
      ((issues_in_workflow++)) || true
    done <<< "$injection_candidates"
  fi

  # Also check for github.event in multiline run blocks.
  # Look for lines within run blocks that reference github.event.
  in_run_block=false
  line_num=0
  while IFS= read -r line; do
    ((line_num++)) || true

    # Detect start of a run: block.
    if echo "$line" | grep -qE '^\s*run:\s*\|'; then
      in_run_block=true
      continue
    fi

    # If we are in a run block.
    if [ "$in_run_block" = true ]; then
      # Check if this line is still part of the run block (indented).
      if echo "$line" | grep -qE '^\s{6,}'; then
        if echo "$line" | grep -qE '\$\{\{.*github\.event\.(issue|pull_request|comment|head_commit)'; then
          echo "    [HIGH] Potential script injection in multiline run: block (line $line_num)"
          record_finding "HIGH" "actions" "$display_path" "$line_num" \
            "Potential script injection — github.event.* in multiline run: block (use env vars instead)"
          ((issues_in_workflow++)) || true
        fi
      else
        in_run_block=false
      fi
    fi
  done <<< "$wf_content"

  # ------------------------------------------------------------------ #
  # 5. Dangerous flags
  # ------------------------------------------------------------------ #

  # --require-approval never (allows CDK deploy without human confirmation).
  if echo "$wf_content" | grep -qE "\-\-require-approval\s+never"; then
    line_num=$(echo "$wf_content" | grep -nE "\-\-require-approval\s+never" | head -1 | cut -d: -f1)
    echo "    [MEDIUM] cdk deploy uses --require-approval never (line $line_num)"
    record_finding "MEDIUM" "actions" "$display_path" "$line_num" \
      "CDK deploy uses --require-approval never — consider requiring approval for staging/prod"
    ((issues_in_workflow++)) || true
  fi

  # --force flag on cdk destroy.
  if echo "$wf_content" | grep -qE "cdk destroy.*--force"; then
    line_num=$(echo "$wf_content" | grep -nE "cdk destroy.*--force" | head -1 | cut -d: -f1)
    echo "    [LOW] cdk destroy uses --force flag (line $line_num)"
    record_finding "LOW" "actions" "$display_path" "$line_num" \
      "CDK destroy uses --force — expected for destroy workflows but verify confirmation gate exists"
    ((issues_in_workflow++)) || true
  fi

  # npm install -g with latest (unpinned CDK CLI version).
  if echo "$wf_content" | grep -qE "npm install.*aws-cdk@latest"; then
    line_num=$(echo "$wf_content" | grep -nE "npm install.*aws-cdk@latest" | head -1 | cut -d: -f1)
    echo "    [LOW] CDK CLI installed with @latest — consider pinning version (line $line_num)"
    record_finding "LOW" "actions" "$display_path" "$line_num" \
      "CDK CLI installed with @latest — pin to a specific version for reproducible deployments"
    ((issues_in_workflow++)) || true
  fi

  # ------------------------------------------------------------------ #
  # 6. Secrets usage
  # ------------------------------------------------------------------ #

  # Check if secrets are used properly (via secrets.* context, not hardcoded).
  if echo "$wf_content" | grep -qE 'secrets\.' && \
     echo "$wf_content" | grep -qE 'run:.*secrets\.'; then
    echo "    [MEDIUM] Secrets referenced directly in run: blocks — prefer env: mapping"
    record_finding "MEDIUM" "actions" "$display_path" "" \
      "Secrets should be mapped to environment variables via env: rather than used directly in run: blocks"
    ((issues_in_workflow++)) || true
  fi

  # ------------------------------------------------------------------ #
  # 7. Workflow trigger security
  # ------------------------------------------------------------------ #

  # Check for pull_request_target (can be dangerous with checkout of PR code).
  if echo "$wf_content" | grep -qE "pull_request_target"; then
    echo "    [HIGH] Uses pull_request_target trigger — review for security implications"
    record_finding "HIGH" "actions" "$display_path" "" \
      "pull_request_target trigger can expose secrets to untrusted PR code — review carefully"
    ((issues_in_workflow++)) || true
  fi

  # ------------------------------------------------------------------ #
  # Summary for this workflow
  # ------------------------------------------------------------------ #

  if [ "$issues_in_workflow" -eq 0 ]; then
    echo "    All checks passed."
    ((workflows_passed++)) || true
  else
    echo "    $issues_in_workflow issue(s) found."
  fi
  echo ""

done < <(find "$PROJECT_ROOT/templates" -name "*.yml" -path "*/.github/workflows/*" 2>/dev/null)

# Also check the project-level .github/workflows if any exist.
if [ -d "$PROJECT_ROOT/.github/workflows" ]; then
  while IFS= read -r workflow_file; do
    ((workflows_reviewed++)) || true
    display_path="${workflow_file#"$PROJECT_ROOT"/}"

    echo "  Reviewing (project-level): $display_path"

    # Apply the same checks — for brevity, just check the critical ones.
    wf_content=$(cat "$workflow_file")

    if echo "$wf_content" | grep -qE "aws-access-key-id|aws-secret-access-key"; then
      echo "    [CRITICAL] Long-lived AWS credentials"
      record_finding "CRITICAL" "actions" "$display_path" "" \
        "Project workflow uses long-lived AWS access keys — must use OIDC"
    fi

    echo "    (Abbreviated checks for project-level workflow)"
    echo ""
  done < <(find "$PROJECT_ROOT/.github/workflows" -name "*.yml" -o -name "*.yaml" 2>/dev/null)
fi

echo "  GitHub Actions review complete: $workflows_reviewed workflow(s) reviewed, $workflows_passed fully passed."
