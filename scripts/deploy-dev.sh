#!/usr/bin/env bash
# Phased FinRAG deploy for config/environments/dev.yaml
#
# Prerequisites:
#   1. source scripts/mfa-session.sh <6-digit-code>   (same terminal)
#   2. .venv activated: source .venv/bin/activate
#
# Usage:
#   ./scripts/deploy-dev.sh              # deploy all stacks in order
#   ./scripts/deploy-dev.sh bootstrap    # bootstrap only
#   ./scripts/deploy-dev.sh synth        # synth only
#   ./scripts/deploy-dev.sh VpcStack     # deploy one stack

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ACCOUNT_ID="539592451537"
REGION="ap-south-1"
BOOTSTRAP_QUALIFIER="aws://${ACCOUNT_ID}/${REGION}"

STACK_ORDER=(
  VpcStack
  StorageStack
  IamStack
  BedrockStack
  PipelineStack
  EventsStack
)

export JSII_RUNTIME_PACKAGE_CACHE=enabled
export JSII_RUNTIME_PACKAGE_CACHE_ROOT="${ROOT}/.jsii-cache"

cdk() {
  npx aws-cdk "$@"
}

require_mfa_session() {
  if [[ -z "${AWS_SESSION_TOKEN:-}" ]]; then
    echo "ERROR: AWS_SESSION_TOKEN is not set." >&2
    echo "Run: source scripts/mfa-session.sh <MFA_CODE>" >&2
    exit 1
  fi
  aws sts get-caller-identity >/dev/null || {
    echo "ERROR: AWS credentials invalid or expired. Refresh MFA session." >&2
    exit 1
  }
  echo "AWS identity:"
  aws sts get-caller-identity
  echo
}

require_venv() {
  if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then
    echo "ERROR: .venv missing. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
  fi
}

run_bootstrap() {
  echo "=== CDK bootstrap (${BOOTSTRAP_QUALIFIER}) ==="
  cdk bootstrap "$BOOTSTRAP_QUALIFIER"
}

run_synth() {
  echo "=== CDK synth (all stacks) ==="
  cdk synth --quiet
  echo "Synth OK."
}

deploy_stack() {
  local stack="$1"
  echo "=== Deploying ${stack} ==="
  cdk deploy "$stack" --require-approval broadening
}

deploy_all() {
  for stack in "${STACK_ORDER[@]}"; do
    deploy_stack "$stack"
  done
  echo
  echo "All stacks deployed."
  cdk list
}

main() {
  require_venv
  require_mfa_session

  case "${1:-all}" in
    bootstrap)
      run_bootstrap
      ;;
    synth)
      run_synth
      ;;
    all)
      run_synth
      run_bootstrap
      deploy_all
      ;;
    *)
      if [[ " ${STACK_ORDER[*]} " != *" $1 "* ]]; then
        echo "Unknown stack: $1" >&2
        echo "Valid stacks: ${STACK_ORDER[*]}" >&2
        exit 1
      fi
      run_synth
      deploy_stack "$1"
      ;;
  esac
}

main "$@"
