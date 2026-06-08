#!/usr/bin/env bash
# Delete the VPC and all resources created by CDK VpcStack.
#
# Usage:
#   source scripts/mfa-session.sh <MFA_CODE>
#   ./scripts/destroy-vpc.sh
#
# Or pass MFA code in one step:
#   ./scripts/destroy-vpc.sh <MFA_CODE>
#
# Skip confirmation:
#   ./scripts/destroy-vpc.sh --yes
#   ./scripts/destroy-vpc.sh <MFA_CODE> --yes

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STACK_NAME="VpcStack"
AWS_CLI="${AWS_CLI:-/opt/homebrew/bin/aws}"

if [[ ! -x "$AWS_CLI" ]]; then
  AWS_CLI="$(command -v aws || true)"
fi

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

import_mfa_session() {
  local code="$1"
  eval "$(
    bash -c "
      source \"${SCRIPT_DIR}/mfa-session.sh\" \"${code}\" >/dev/null
      printf 'export AWS_ACCESS_KEY_ID=%q\n' \"\$AWS_ACCESS_KEY_ID\"
      printf 'export AWS_SECRET_ACCESS_KEY=%q\n' \"\$AWS_SECRET_ACCESS_KEY\"
      printf 'export AWS_SESSION_TOKEN=%q\n' \"\$AWS_SESSION_TOKEN\"
    "
  )" || fail "Could not start MFA session. Use a fresh 6-digit CheshtaPhone code."
}

MFA_CODE=""
AUTO_YES=false

for arg in "$@"; do
  case "$arg" in
    --yes|-y) AUTO_YES=true ;;
    [0-9][0-9][0-9][0-9][0-9][0-9]) MFA_CODE="$arg" ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

if [[ -z "${AWS_SESSION_TOKEN:-}" ]]; then
  if [[ -n "$MFA_CODE" ]]; then
    echo "Starting MFA session..."
    import_mfa_session "$MFA_CODE"
  else
    fail "MFA session required. Run: source scripts/mfa-session.sh <CODE>  OR  ./scripts/destroy-vpc.sh <CODE>"
  fi
fi

cd "$PROJECT_ROOT"

echo "AWS identity:"
"$AWS_CLI" sts get-caller-identity

echo
echo "This will DELETE CloudFormation stack: ${STACK_NAME}"
echo "Region: ap-south-1 | Account: 539592451537"
echo "Includes: VPC (VPC-Nivyo-Dev), subnets, IGW, routes, S3 gateway endpoint,"
echo "           security groups, VPC flow logs, and related resources."
echo

if [[ "$AUTO_YES" != true ]]; then
  read -r -p "Type 'delete' to confirm: " CONFIRM
  if [[ "$CONFIRM" != "delete" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo "Destroying ${STACK_NAME}..."
npx aws-cdk destroy "$STACK_NAME" --force

echo
echo "Done. Verify in AWS Console (VPC, ap-south-1) that resources are removed."
