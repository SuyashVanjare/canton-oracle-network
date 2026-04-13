# Copyright (c) 2024 Digital Asset (Canton) LLC and/or its affiliates. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
import requests
from decimal import Decimal
from typing import Optional

# Configure logging for the module
logger = logging.getLogger(__name__)

class EquitySource:
    """
    Data source adapter for fetching equity spot prices from the Finnhub API.
    
    This class handles the communication with the Finnhub API to retrieve
    the latest quote for a given equity ticker symbol. It requires an API
    key to be configured via the `FINNHUB_API_KEY` environment variable.
    """
    API_BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        """
        Initializes the EquitySource.
        
        Raises:
            ValueError: If the FINNHUB_API_KEY environment variable is not set.
        """
        self.api_key = os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            msg = "FINNHUB_API_KEY environment variable not set. Please provide a valid API key."
            logger.error(msg)
            raise ValueError(msg)
        
        self.session = requests.Session()
        self.session.headers.update({'X-Finnhub-Token': self.api_key})
        logger.info("EquitySource initialized using Finnhub API.")

    def get_price(self, ticker: str) -> Optional[Decimal]:
        """
        Fetches the latest spot price for a given equity ticker.

        Args:
            ticker: The stock ticker symbol (e.g., 'AAPL' for Apple Inc.).

        Returns:
            The current price as a Decimal object, or None if the fetch fails,
            the ticker is invalid, or no price is available.
        """
        if not isinstance(ticker, str) or not ticker.strip():
            logger.warning(f"Invalid ticker provided: '{ticker}'. Ticker must be a non-empty string.")
            return None

        symbol = ticker.upper().strip()
        endpoint = f"{self.API_BASE_URL}/quote"
        params = {'symbol': symbol}

        try:
            logger.debug(f"Requesting quote for equity ticker: {symbol}")
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            logger.debug(f"Received API response for {symbol}: {data}")

            # 'c' represents the current price in the Finnhub quote response.
            # A price of 0 or None can indicate no recent trade data, especially
            # for illiquid assets or when markets are closed.
            current_price = data.get('c')
            if current_price is None or float(current_price) == 0.0:
                logger.warning(f"No valid current price available for {symbol}. API response: {data}")
                return None

            price_decimal = Decimal(str(current_price))
            logger.info(f"Successfully fetched price for {symbol}: {price_decimal}")
            return price_decimal

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred while fetching {symbol}: {http_err}. Response: {response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred while fetching {symbol}: {conn_err}")
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out while fetching {symbol}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An unexpected request error occurred while fetching {symbol}: {req_err}")
        except (ValueError, KeyError) as parse_err:
            logger.error(f"Failed to parse API response for {symbol}: {parse_err}. Response: {response.text}")
        
        return None

if __name__ == '__main__':
    # This block allows for direct testing of the EquitySource module.
    # To run, set the FINNHUB_API_KEY environment variable:
    # export FINNHUB_API_KEY='your_finnhub_api_key'
    # python -m publisher.sources.equity
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("--- Running EquitySource Test ---")
    if not os.getenv("FINNHUB_API_KEY"):
        print("\nERROR: FINNHUB_API_KEY is not set. Cannot run tests.")
        print("Please set it and try again.")
    else:
        try:
            source = EquitySource()

            # Test case 1: Valid and highly liquid ticker
            print("\nFetching price for Apple (AAPL)...")
            aapl_price = source.get_price("AAPL")
            if aapl_price:
                print(f"  -> Success! Current AAPL price: ${aapl_price}")
            else:
                print("  -> Failed to get AAPL price.")

            # Test case 2: Another valid ticker
            print("\nFetching price for Microsoft (MSFT)...")
            msft_price = source.get_price("MSFT")
            if msft_price:
                print(f"  -> Success! Current MSFT price: ${msft_price}")
            else:
                print("  -> Failed to get MSFT price.")

            # Test case 3: Invalid ticker
            print("\nFetching price for an invalid ticker (INVALIDTICKER123)...")
            invalid_price = source.get_price("INVALIDTICKER123")
            if not invalid_price:
                print("  -> Success! Correctly handled invalid ticker.")
            else:
                print("  -> Failure! Expected None for invalid ticker.")
            
            # Test case 4: Empty string ticker
            print("\nFetching price for an empty ticker ('')...")
            empty_price = source.get_price("")
            if not empty_price:
                print("  -> Success! Correctly handled empty ticker.")
            else:
                print("  -> Failure! Expected None for empty ticker.")

        except ValueError as e:
            print(f"\nInitialization failed: {e}")
            
    print("\n--- Test Complete ---")