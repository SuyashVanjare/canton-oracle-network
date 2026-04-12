# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.0] - 2024-05-21

### Added

- **Daml Models**: Initial smart contract implementation for the core oracle network logic.
  - `Oracle.Subscription`: Manages the lifecycle of data subscriptions, allowing consumers to request access to specific price feeds from the oracle network operator. Includes a proposal/acceptance workflow for new subscriptions.
  - `Oracle.Dispute`: Defines the on-chain dispute resolution process. Consumers can raise disputes against published price points, triggering a review process.

- **Publisher SDK**: A Python-based client (`publisher/`) for data providers to connect and publish data to the Canton network.
  - `publisher/main.py`: Main entrypoint for the publisher service, handling command-line arguments and connecting to the ledger.
  - `publisher/sources/forex.py`: Initial data source connector for Forex (FX) rates (e.g., EUR/USD).

- **Testing**:
  - `daml/test/OracleTest.daml`: A Daml Script test suite covering the happy path for subscription creation and basic dispute initiation, ensuring the core logic is sound.

- **Project Configuration**:
  - `daml.yaml` configured for Canton 3.4 with standard dependencies (`daml-prim`, `daml-stdlib`, `daml-script`).
  - `.gitignore` tailored for Daml and Python projects.