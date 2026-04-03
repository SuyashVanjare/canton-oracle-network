# Oracle Consumer Guide

## Integrating Canton Oracle Network into your DeFi app

### Step 1 — Subscribe to a price feed

```daml
import Oracle.Subscription

subCid <- create PriceFeedSubscription with
  consumer  = myApp
  authority = oracleAuthority
  pair      = "EUR/USD"
  maxAge    = RelTime 300_000_000  -- 5 minutes in microseconds
```

### Step 2 — Fetch the latest aggregated price

```daml
import Oracle.Aggregator

-- Query the latest AggregatedPrice for EUR/USD
-- In Daml Script:
prices <- queryContractKey @AggregatedPrice (oracleAuthority, "EUR/USD")
case prices of
  Some (_, agg) -> do
    let rate = agg.aggregatedPrice
    -- use rate in your DeFi logic
  None -> abort "No oracle price available"
```

### Step 3 — Enforce freshness in your contract

```daml
-- In your contract choice:
now <- getTime
assertMsg "Oracle price is stale" $
  now `subTime` agg.computedAt < days 0  -- within 5 minutes
```

### Privacy

The `AggregatedPrice` contract is visible to:
- The Oracle Authority (signatory)
- Subscribed consumers (observer via subscription)

Individual provider feeds are **not** visible to consumers — only the
aggregated result is exposed, preserving provider data confidentiality.

### Supported pairs

| Category | Pairs |
|----------|-------|
| FX       | EUR/USD, EUR/GBP, EUR/JPY, EUR/CHF, GBP/USD |
| Rates    | UST/2Y, UST/5Y, UST/10Y, UST/30Y |
| Crypto   | BTC/USD, ETH/USD (via approved providers) |
