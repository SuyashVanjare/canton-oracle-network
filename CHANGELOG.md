# Changelog — Canton Oracle Network

## [0.3.0] — 2026-04-03

### Added
- Full oracle contract suite: `PriceFeed`, `Aggregator`, `ProviderRegistry`, `Dispute`, `Subscription`
- Trimmed-median aggregation (trimming bottom/top 20% to resist outliers)
- Python publisher SDK with async price submission loop
- FX rate adapter: ECB + fallback rates for EUR/USD, EUR/GBP, EUR/JPY, EUR/CHF
- US Treasury yield adapter: FRED API with fallback static yields
- Daml tests: multi-provider aggregation + outlier rejection
- CI pipeline (Daml build + test + Python lint)
- Provider guide (registration, SLA, dispute resolution)
- Consumer integration guide (subscribe, fetch, freshness enforcement)

## [0.2.0] — 2026-03-22

### Added
- `PriceFeed.daml` — data provider submission contract
- `ProviderRegistry.daml` — stake-weighted provider approval registry
- `Dispute.daml` — on-chain challenge for outlier submissions

## [0.1.0] — 2026-03-15

### Added
- Initial project scaffolding, README, daml.yaml
