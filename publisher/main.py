# publisher/main.py

# This script acts as a data publisher for the Canton Oracle Network.
# It periodically fetches price data from an external source (e.g., Coinbase)
# and submits it as an observation to an Aggregator contract on a Canton ledger
# via the Canton Participant's JSON API.

# --- Dependencies ---
# To run this script, you need to install the required Python packages:
# pip install requests python-dotenv

import os
import requests
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal
from dotenv import load_dotenv

# --- Configuration ---

# Load environment variables from a .env file
load_dotenv()

# Configure logging for visibility into the script's operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OraclePublisher")

# Canton JSON API Configuration
JSON_API_URL = os.getenv("CANTON_JSON_API_URL")
AUTH_TOKEN = os.getenv("CANTON_AUTH_TOKEN") # This token must be a valid JWT for the participant
PUBLISHER_PARTY_ID = os.getenv("PUBLISHER_PARTY_ID")

# Publisher-specific Configuration
# The asset this publisher instance is responsible for (e.g., "BTC/USD", "EUR/USD")
ASSET_LABEL = os.getenv("ASSET_LABEL", "BTC/USD")
# How often to fetch and submit data, in seconds
SUBMISSION_INTERVAL_SECONDS = int(os.getenv("SUBMISSION_INTERVAL_SECONDS", "30"))

# Daml Template IDs
# These must match the template identifiers in your Daml project's DAR file.
AGGREGATOR_TEMPLATE_ID = "Oracle.Aggregator:Aggregator"


# --- External Data Fetching ---

def fetch_external_price(asset_label: str) -> Decimal | None:
    """
    Fetches the current price for a given asset from an external API.
    This example uses the Coinbase API for BTC/USD.
    It can be extended to support other assets or data sources.
    """
    if asset_label == "BTC/USD":
        try:
            url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            price = Decimal(data['data']['amount'])
            logger.info(f"Fetched {asset_label} price from Coinbase: {price}")
            return price
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching price from Coinbase API: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing price data from Coinbase response: {e}")
            return None
    else:
        logger.warning(f"No data source configured for asset label: {asset_label}")
        return None


# --- Canton Ledger Interaction via JSON API ---

def get_json_api_headers() -> dict:
    """Constructs the required headers for JSON API requests."""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

def find_aggregator_contract(asset_label: str, party_id: str) -> dict | None:
    """
    Queries the ledger for an active Aggregator contract for the specified asset.
    Returns the first matching contract found.
    """
    headers = get_json_api_headers()
    query = {
        "templateIds": [AGGREGATOR_TEMPLATE_ID],
    }

    logger.info(f"Querying for '{asset_label}' Aggregator contract...")
    try:
        response = requests.post(f"{JSON_API_URL}/v1/query", headers=headers, json=query, timeout=10)
        response.raise_for_status()
        contracts = response.json().get('result', [])

        for contract in contracts:
            # Filter the results to find the contract with the matching label
            if contract.get('payload', {}).get('label') == asset_label:
                logger.info(f"Found active Aggregator contract: {contract['contractId']}")
                return contract

        logger.warning(f"No active Aggregator contract found for label '{asset_label}'.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to query for Aggregator contracts: {e}")
        return None

def submit_observation_to_ledger(contract_id: str, price: Decimal, party_id: str):
    """
    Exercises the 'SubmitObservation' choice on the specified Aggregator contract.
    """
    headers = get_json_api_headers()

    # Timestamps in Daml are expected in ISO 8601 format with UTC timezone.
    observation_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # The choice argument must match the Daml model's 'SubmitObservation' choice definition.
    # Daml's 'Decimal' type is represented as a string in JSON.
    choice_argument = {
        "provider": party_id,
        "observation": {
            "value": str(price),
            "timestamp": observation_time
        }
    }

    payload = {
        "templateId": AGGREGATOR_TEMPLATE_ID,
        "contractId": contract_id,
        "choice": "SubmitObservation",
        "argument": choice_argument
    }

    logger.info(f"Submitting observation to {contract_id}: Value={price}, Timestamp={observation_time}")
    try:
        response = requests.post(f"{JSON_API_URL}/v1/exercise", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully exercised 'SubmitObservation' on contract {contract_id}")
        return response.json().get('result')
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to exercise 'SubmitObservation' on {contract_id}: {e}")
        # Log detailed error from the JSON API if available
        try:
            error_details = e.response.json()
            logger.error(f"API Error details: {error_details}")
        except (ValueError, AttributeError):
            logger.error(f"Could not parse error details from API response.")
        return None


# --- Main Application Logic ---

def main_loop():
    """Main execution loop for the publisher."""
    while True:
        # 1. Fetch the latest price from the external data source.
        price = fetch_external_price(ASSET_LABEL)

        if price is not None:
            # 2. Find the target Aggregator contract on the Canton ledger.
            # We look this up every time to handle contract churn (e.g., if the
            # aggregator is upgraded or archived/recreated).
            aggregator_contract = find_aggregator_contract(ASSET_LABEL, PUBLISHER_PARTY_ID)

            if aggregator_contract:
                # 3. If an aggregator is found, submit the observation.
                submit_observation_to_ledger(
                    contract_id=aggregator_contract['contractId'],
                    price=price,
                    party_id=PUBLISHER_PARTY_ID
                )
            else:
                logger.warning("Skipping submission as no target contract was found.")
        else:
            logger.error("Failed to fetch external price data. Skipping submission cycle.")

        # 4. Wait for the specified interval before the next cycle.
        logger.info(f"Waiting for {SUBMISSION_INTERVAL_SECONDS} seconds...")
        time.sleep(SUBMISSION_INTERVAL_SECONDS)


if __name__ == "__main__":
    # Perform startup checks
    if not all([JSON_API_URL, AUTH_TOKEN, PUBLISHER_PARTY_ID]):
        logger.critical(
            "CRITICAL: Missing required environment variables. "
            "Please set CANTON_JSON_API_URL, CANTON_AUTH_TOKEN, and PUBLISHER_PARTY_ID."
        )
        exit(1)

    logger.info("--- Oracle Publisher Service Starting ---")
    logger.info(f"Publisher Party ID: {PUBLISHER_PARTY_ID}")
    logger.info(f"Target Asset: {ASSET_LABEL}")
    logger.info(f"JSON API Endpoint: {JSON_API_URL}")
    logger.info(f"Submission Interval: {SUBMISSION_INTERVAL_SECONDS} seconds")
    logger.info("---------------------------------------")

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Publisher service shutting down.")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        exit(1)