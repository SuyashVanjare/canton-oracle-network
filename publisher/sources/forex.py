import abc
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Optional
from decimal import Decimal, getcontext

# Set precision for Decimal to handle financial calculations accurately
getcontext().prec = 28

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_XML_NAMESPACE = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}"


class ForexSource(abc.ABC):
    """Abstract base class for a foreign exchange rate data source."""

    @abc.abstractmethod
    def get_rate(self, base_currency: str, quote_currency: str) -> Decimal:
        """
        Fetches the exchange rate for a given currency pair.

        Args:
            base_currency: The three-letter currency code of the base currency (e.g., 'USD').
            quote_currency: The three-letter currency code of the quote currency (e.g., 'JPY').

        Returns:
            The exchange rate as a Decimal, representing how many units of the
            quote currency are needed to buy one unit of the base currency.

        Raises:
            ValueError: If the currency pair is invalid or not found.
            IOError: If there's an issue fetching data from the source.
        """
        pass

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """The official name of the data source."""
        pass


class ECBSource(ForexSource):
    """
    Forex data source using the European Central Bank (ECB) daily reference rates.
    Note: All rates are published against the EUR. Cross-rates are calculated automatically.
    """
    def __init__(self, cache_duration_seconds: int = 3600):
        self._cache_duration = timedelta(seconds=cache_duration_seconds)
        self._cached_rates: Optional[Dict[str, Decimal]] = None
        self._cache_expiry: Optional[datetime] = None

    @property
    def source_name(self) -> str:
        return "European Central Bank"

    def _is_cache_valid(self) -> bool:
        """Checks if the cached data is still valid."""
        return (
            self._cached_rates is not None and
            self._cache_expiry is not None and
            datetime.utcnow() < self._cache_expiry
        )

    def _fetch_and_parse_rates(self):
        """Fetches XML data from the ECB and parses it into a rates dictionary."""
        logger.info(f"Fetching fresh FX rates from {self.source_name}...")
        try:
            response = requests.get(ECB_RATES_URL, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

            root = ET.fromstring(response.content)

            # The structure is <Cube><Cube time='...'><Cube currency='USD' rate='...'/>...</Cube></Cube>
            rates_container = root.find(f'.//{ECB_XML_NAMESPACE}Cube[@time]')
            if rates_container is None:
                raise ValueError("Could not find the rates container in ECB XML response.")

            rates: Dict[str, Decimal] = {"EUR": Decimal("1.0")}
            for currency_node in rates_container.findall(f'{ECB_XML_NAMESPACE}Cube[@currency]'):
                currency = currency_node.get('currency')
                rate_str = currency_node.get('rate')
                if currency and rate_str:
                    rates[currency] = Decimal(rate_str)

            self._cached_rates = rates
            self._cache_expiry = datetime.utcnow() + self._cache_duration
            logger.info(f"Successfully fetched and cached {len(rates)} rates from ECB.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching data from ECB: {e}")
            raise IOError("Could not connect to the ECB data source.") from e
        except ET.ParseError as e:
            logger.error(f"Error parsing XML from ECB: {e}")
            raise ValueError("Invalid XML format received from ECB.") from e

    def get_rate(self, base_currency: str, quote_currency: str) -> Decimal:
        """
        Calculates the exchange rate for a pair, using EUR as the pivot currency.
        """
        base = base_currency.upper()
        quote = quote_currency.upper()

        if base == quote:
            return Decimal("1.0")

        if not self._is_cache_valid():
            self._fetch_and_parse_rates()

        if self._cached_rates is None:
            raise RuntimeError("Rate cache is empty even after attempting to fetch.")

        if base not in self._cached_rates:
            raise ValueError(f"Base currency '{base}' not found in ECB data.")
        if quote not in self._cached_rates:
            raise ValueError(f"Quote currency '{quote}' not found in ECB data.")

        # All rates are against EUR, e.g., self._cached_rates['USD'] is the EUR/USD rate.
        # To calculate BASE/QUOTE, we use (EUR/QUOTE) / (EUR/BASE).
        eur_per_base = self._cached_rates[base]
        eur_per_quote = self._cached_rates[quote]

        if eur_per_base == Decimal(0):
            raise ValueError("EUR per base currency rate is zero, cannot calculate cross-rate.")

        rate = eur_per_quote / eur_per_base
        logger.info(f"Calculated rate for {base}/{quote}: {rate} (Source: {self.source_name})")
        return rate


class BloombergBridgeSource(ForexSource):
    """
    Mock forex data source simulating a connection to a Bloomberg Terminal or B-PIPE.

    NOTE: This is a placeholder for development. A real implementation would require
    the 'blpapi' library and proper authentication and connection details for a
    Bloomberg service.
    """
    def __init__(self, host: str = "localhost", port: int = 8194):
        self.host = host
        self.port = port
        logger.warning(f"Initialized {self.source_name}. This is not connected to a real Bloomberg service.")

    @property
    def source_name(self) -> str:
        return "Bloomberg Bridge (Mock)"

    def get_rate(self, base_currency: str, quote_currency: str) -> Decimal:
        """
        Returns a hardcoded, mock exchange rate for demonstration purposes.
        """
        pair = f"{base_currency.upper()}{quote_currency.upper()}"
        logger.info(f"Requesting mock rate for {pair} from {self.source_name}...")

        # A real implementation would connect to the Bloomberg API using blpapi
        # and request the `PX_LAST` field for a security like `EURUSD Curncy`.
        # This section is mocked for simplicity.

        mock_rates = {
            "EURUSD": Decimal("1.0855"),
            "USDJPY": Decimal("157.12"),
            "GBPUSD": Decimal("1.2610"),
            "AUDUSD": Decimal("0.6650"),
            "USDCAD": Decimal("1.3678"),
            "USDCHF": Decimal("0.9015"),
        }

        if pair in mock_rates:
            return mock_rates[pair]
        else:
            logger.error(f"Mock rate for '{pair}' not available in {self.source_name}.")
            raise NotImplementedError(f"The mock Bloomberg bridge does not have a rate for {pair}.")


# --- Example Usage ---
# This block demonstrates how to use the data source classes.
# It will only run when the script is executed directly.
if __name__ == "__main__":
    print("--- Testing Canton Oracle Network: Forex Data Sources ---")

    print("\n[1] Testing ECB Data Source...")
    try:
        ecb_source = ECBSource()

        # Test 1: Direct rate (EUR base)
        eur_usd_rate = ecb_source.get_rate("EUR", "USD")
        print(f"  EUR/USD Rate: {eur_usd_rate}")

        # Test 2: Inverted rate (EUR quote)
        usd_eur_rate = ecb_source.get_rate("USD", "EUR")
        print(f"  USD/EUR Rate: {usd_eur_rate}")
        print(f"    -> Inverse check: 1 / {eur_usd_rate} = {1/eur_usd_rate:.8f}")

        # Test 3: Cross rate calculation
        gbp_jpy_rate = ecb_source.get_rate("GBP", "JPY")
        print(f"  GBP/JPY Rate: {gbp_jpy_rate}")

        # Test 4: Invalid currency
        try:
            ecb_source.get_rate("USD", "XYZ")
        except ValueError as e:
            print(f"  Successfully caught expected error: {e}")

    except (IOError, ValueError) as e:
        print(f"  An error occurred with the ECB source: {e}")

    print("\n[2] Testing Bloomberg Bridge (Mock) Source...")
    try:
        bbg_source = BloombergBridgeSource()

        # Test 1: Supported mock pair
        eur_usd_mock = bbg_source.get_rate("EUR", "USD")
        print(f"  Mock EUR/USD Rate: {eur_usd_mock}")

        # Test 2: Unsupported mock pair
        try:
            bbg_source.get_rate("AUD", "NZD")
        except NotImplementedError as e:
            print(f"  Successfully caught expected error: {e}")

    except Exception as e:
        print(f"  An error occurred with the Bloomberg source: {e}")