#!/usr/bin/env bash
# register-provider.sh — Register as an approved Canton Oracle provider.
set -euo pipefail

CANTON_HOST="${CANTON_HOST:-localhost}"
CANTON_PORT="${CANTON_PORT:-7575}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
AUTHORITY="${AUTHORITY_PARTY:-}"
PROVIDER="${PROVIDER_PARTY:-}"
STAKE="${STAKE:-10000.0}"

usage() {
  echo "Usage: AUTHORITY_PARTY=... PROVIDER_PARTY=... AUTH_TOKEN=... $0"
  exit 1
}

[[ -z "$AUTHORITY" ]] && { echo "Error: AUTHORITY_PARTY env required"; usage; }
[[ -z "$PROVIDER"  ]] && { echo "Error: PROVIDER_PARTY env required";  usage; }
[[ -z "$AUTH_TOKEN" ]] && { echo "Error: AUTH_TOKEN env required";      usage; }

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Registering oracle provider..."
echo "  Provider  : $PROVIDER"
echo "  Authority : $AUTHORITY"
echo "  Stake     : $STAKE CC"
echo ""

curl -sf   -H "Authorization: Bearer $AUTH_TOKEN"   -H "Content-Type: application/json"   "http://${CANTON_HOST}:${CANTON_PORT}/v1/create"   -d @- << JSON
{
  "templateId": "Oracle:ProviderRegistry:ProviderRegistration",
  "payload": {
    "provider":    "$PROVIDER",
    "authority":   "$AUTHORITY",
    "stake":       $STAKE,
    "approvedAt":  "$NOW"
  }
}
JSON

echo ""
echo "Provider registered. Start the publisher with:"
echo "  python -m publisher.main --provider '$PROVIDER' --authority '$AUTHORITY'"
