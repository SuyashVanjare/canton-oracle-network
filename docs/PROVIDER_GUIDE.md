# Oracle Provider Guide

## Becoming an approved oracle provider

### 1. Register with the CNS Authority

Contact the Oracle Network Authority to be added to the `ProviderRegistry`.
You will need to stake **10,000 CC** as a security deposit, slashable on misbehaviour.

### 2. Run the publisher SDK

```bash
pip install httpx
export CANTON_HOST=your-canton-node.example.com
export CANTON_PORT=7575
export AUTH_TOKEN=your-jwt
export PROVIDER_PARTY="YourOrg::..."
export AUTHORITY_PARTY="OracleAuthority::..."

python -m publisher.main --interval 60
```

### 3. Supported data sources

| Source | Pairs |
|--------|-------|
| ECB    | EUR/USD, EUR/GBP, EUR/JPY, EUR/CHF |
| US Treasury (FRED) | UST/2Y, UST/5Y, UST/10Y, UST/30Y |
| Custom bridge | Any pair via `publisher/sources/` |

### 4. SLA requirements

| Metric | Requirement |
|--------|-------------|
| Feed freshness | ≤ 5 minutes per pair |
| Uptime | ≥ 99.5% (30-day rolling) |
| Accuracy | Within 0.1% of trimmed median |

Consistent outlier submissions trigger an on-chain `Dispute` contract and may
result in stake slashing by the authority.

### 5. Dispute resolution

If your feed is flagged as an outlier, you receive a `Dispute` contract on your
ledger. You have **24 hours** to respond with evidence of a legitimate price.
Unresolved disputes result in partial stake slashing.
