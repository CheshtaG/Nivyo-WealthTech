#!/usr/bin/env bash
# Usage (must source in zsh/bash — do NOT run with ./):
#   source scripts/mfa-session.sh
#   source scripts/mfa-session.sh 123456

mfa_session_fail() {
  echo "ERROR: $1" >&2
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Run with: source scripts/mfa-session.sh [MFA_CODE]" >&2
  exit 1
fi

MFA_SERIAL="arn:aws:iam::539592451537:mfa/CheshtaPhone"
AWS_CLI="${AWS_CLI:-/opt/homebrew/bin/aws}"

if [[ ! -x "$AWS_CLI" ]]; then
  AWS_CLI="$(command -v aws || true)"
fi
if [[ -z "$AWS_CLI" ]]; then
  mfa_session_fail "aws CLI not found. Install with: brew install awscli"
  return 1
fi

if [[ -n "${1:-}" ]]; then
  MFA_CODE="$1"
else
  if [[ ! -t 0 ]]; then
    mfa_session_fail "No MFA code provided and terminal is not interactive. Use: source scripts/mfa-session.sh 123456"
    return 1
  fi
  read -r -p "Enter 6-digit MFA code from CheshtaPhone: " MFA_CODE
fi

if [[ ! "$MFA_CODE" =~ ^[0-9]{6}$ ]]; then
  mfa_session_fail "MFA code must be exactly 6 digits."
  return 1
fi

SESSION_JSON="$("$AWS_CLI" sts get-session-token \
  --serial-number "$MFA_SERIAL" \
  --token-code "$MFA_CODE" \
  --duration-seconds 43200 \
  --output json 2>/dev/null)" || {
  mfa_session_fail "get-session-token failed. Use a fresh code from CheshtaPhone authenticator."
  return 1
}

AWS_ACCESS_KEY_ID="$(echo "$SESSION_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")"
AWS_SECRET_ACCESS_KEY="$(echo "$SESSION_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")"
AWS_SESSION_TOKEN="$(echo "$SESSION_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['Credentials']['SessionToken'])")"

if [[ -z "$AWS_SESSION_TOKEN" ]]; then
  mfa_session_fail "Could not parse session credentials from AWS response."
  return 1
fi

export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

echo "MFA session active."
"$AWS_CLI" sts get-caller-identity
echo
echo "AWS_SESSION_TOKEN is set. Deploy with:"
echo '  npx aws-cdk bootstrap aws://539592451537/ap-south-1'
echo '  npx aws-cdk deploy VpcStack'
