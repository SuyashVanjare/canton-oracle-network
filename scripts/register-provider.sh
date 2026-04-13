#!/bin/bash

# ==============================================================================
# Register as an Oracle Provider
#
# Description:
#   This script registers a new data provider with the Canton Oracle Network.
#   It finds the central Oracle Service contract, finds a suitable asset owned
#   by the provider to use as stake, and exercises the `RegisterProvider`
#   choice to complete the registration.
#
# Prerequisites:
#   - `curl` and `jq` must be installed and in the PATH.
#   - A Canton ledger with the Oracle contracts must be running.
#   - The Oracle Operator must have already deployed the `Oracle.Service` contract.
#
# Environment Variables:
#   - PROVIDER_PARTY: The Party ID of the provider to be registered. (Required)
#   - PROVIDER_JWT:   A valid JWT for the PROVIDER_PARTY. (Required)
#   - JSON_API_URL:   The URL of the Canton ledger's JSON API.
#                     (Default: http://localhost:7575)
#   - OPERATOR_PARTY: The Party ID of the Oracle Network operator. (Required)
#
# Usage:
#   export PROVIDER_PARTY="..."
#   export PROVIDER_JWT="..."
#   export OPERATOR_PARTY="..."
#   ./scripts/register-provider.sh "My FX Feed" "10000.0"
#
# Arguments:
#   $1: displayName  - The public display name for the new provider.
#   $2: stakeAmount  - The amount of the asset to stake. Must be a valid Decimal.
#
# ==============================================================================

set -euo pipefail

# --- Configuration and Argument Parsing ---------------------------------------

JSON_API_URL=${JSON_API_URL:-"http://localhost:7575"}
: "${PROVIDER_PARTY:?Error: PROVIDER_PARTY environment variable is not set.}"
: "${PROVIDER_JWT:?Error: PROVIDER_JWT environment variable is not set.}"
: "${OPERATOR_PARTY:?Error: OPERATOR_PARTY environment variable is not set.}"

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <displayName> <stakeAmount>"
    echo "Example: $0 \"My FX Feed\" \"10000.0\""
    echo ""
    echo "Please set PROVIDER_PARTY, PROVIDER_JWT, and OPERATOR_PARTY environment variables."
    exit 1
fi

DISPLAY_NAME="$1"
STAKE_AMOUNT="$2"

# Assumed template IDs. Replace if your model uses different names.
SERVICE_TEMPLATE_ID="Oracle.Service:Service"
PROVIDER_TEMPLATE_ID="Oracle.Provider:Provider"
# Using a common standard fungible asset template.
ASSET_TEMPLATE_ID="Daml.Finance.Asset.Fungible:Fungible"


# --- Helper Functions ---------------------------------------------------------

# Function to make authenticated requests to the JSON API
# $1: endpoint (e.g., "/v1/query")
# $2: payload (JSON string)
function api_request() {
    local endpoint="$1"
    local payload="$2"

    curl --silent --show-error -X POST "${JSON_API_URL}${endpoint}" \
        -H "Authorization: Bearer ${PROVIDER_JWT}" \
        -H "Content-Type: application/json" \
        -d "${payload}"
}

# --- Main Logic ---------------------------------------------------------------

echo "▶️  Starting provider registration for '${DISPLAY_NAME}' acting as Party: ${PROVIDER_PARTY}"

# 1. Find the Oracle Service contract
echo "1️⃣  Searching for the Oracle Service contract operated by ${OPERATOR_PARTY}..."

query_payload=$(jq -n --arg tid "$SERVICE_TEMPLATE_ID" '{templateIds: [$tid]}')
query_response=$(api_request "/v1/query" "$query_payload")

service_cid=$(echo "$query_response" | jq -r --arg op "$OPERATOR_PARTY" '.result[] | select(.payload.operator == $op) | .contractId')

if [[ -z "$service_cid" ]]; then
    echo "❌ Error: Could not find an active '${SERVICE_TEMPLATE_ID}' contract for operator ${OPERATOR_PARTY}."
    echo "Response from ledger: ${query_response}"
    exit 1
fi
echo "✅ Found Oracle Service contract: ${service_cid}"


# 2. Find a suitable asset for staking
echo "2️⃣  Searching for a suitable asset contract owned by the provider to stake ${STAKE_AMOUNT}..."

asset_query_payload=$(jq -n --arg tid "$ASSET_TEMPLATE_ID" '{templateIds: [$tid]}')
asset_query_response=$(api_request "/v1/query" "$asset_query_payload")

# Filter for an asset owned by the provider with sufficient quantity
stake_asset_cid=$(echo "$asset_query_response" | jq -r --arg pty "$PROVIDER_PARTY" --arg amt "$STAKE_AMOUNT" '
    .result[] |
    select(.payload.owner == $pty and (.payload.quantity | tonumber) >= ($amt | tonumber)) |
    .contractId' | head -n 1)

if [[ -z "$stake_asset_cid" ]]; then
    echo "❌ Error: Could not find a suitable '${ASSET_TEMPLATE_ID}' contract owned by ${PROVIDER_PARTY} with at least ${STAKE_AMOUNT}."
    echo "Ensure the provider has a fungible asset contract on the ledger."
    exit 1
fi
echo "✅ Found asset contract for staking: ${stake_asset_cid}"


# 3. Exercise the RegisterProvider choice
echo "3️⃣  Exercising 'RegisterProvider' choice on the service contract..."

exercise_payload=$(jq -n \
    --arg tid "$SERVICE_TEMPLATE_ID" \
    --arg cid "$service_cid" \
    --arg name "$DISPLAY_NAME" \
    --arg amt "$STAKE_AMOUNT" \
    --arg sacid "$stake_asset_cid" \
    '{
        "templateId": $tid,
        "contractId": $cid,
        "choice": "RegisterProvider",
        "argument": {
            "displayName": $name,
            "stakeAmount": $amt,
            "stakeAssetCid": $sacid
        }
    }')

exercise_response=$(api_request "/v1/exercise" "$exercise_payload")

# Check for errors in the response
if [[ $(echo "$exercise_response" | jq '.status') != "200" ]]; then
    echo "❌ Error: Failed to exercise 'RegisterProvider' choice."
    echo "Response from ledger:"
    echo "$exercise_response" | jq
    exit 1
fi

# Extract the newly created Provider contract ID from the events
provider_cid=$(echo "$exercise_response" | jq -r --arg tid "$PROVIDER_TEMPLATE_ID" '.result.events[] | select(.created.templateId == $tid) | .created.contractId')

if [[ -z "$provider_cid" ]]; then
    echo "⚠️  Warning: Provider registration transaction submitted, but could not find the new Provider contract ID in the response."
    echo "Please check the ledger manually."
else
    echo "✅ Successfully registered as a provider!"
    echo "   New Provider Contract ID: ${provider_cid}"
fi

echo "🏁 Registration complete."