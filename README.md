# Canton Oracle Network

## Overview

The Canton Oracle Network provides a decentralized and reliable mechanism for delivering off-chain data to Canton-based smart contracts. It's designed to be:

*   **Canton-Native:** Built specifically for the Canton Network, leveraging its privacy and interoperability features.
*   **Decentralized:** Data is sourced from multiple independent providers, reducing the risk of single points of failure.
*   **Privacy-Preserving:** Aggregation of data is handled in a way that minimizes the exposure of individual provider data.
*   **Institutional-Grade:** Focuses on high-quality data feeds suitable for institutional DeFi applications, covering asset classes like FX rates, Treasury yields, equity prices, and crypto prices.
*   **Dispute Resolution:** Includes on-chain mechanisms for resolving disputes related to data accuracy.

This project aims to be the "Chainlink equivalent" for institutional Canton DeFi.

## Architecture

The network consists of the following key components:

1.  **Data Providers:** Entities that supply data to the network (e.g., banks, financial data vendors). They are permissioned and onboarded by the network operator.

2.  **Oracle Aggregator:** A Canton smart contract responsible for collecting data from providers, performing aggregation, and providing the aggregated value to consuming applications. The aggregation logic is configurable.

3.  **Data Consumers:** Canton-based smart contracts that rely on the oracle's data feeds.

4.  **Dispute Resolution Mechanism:** On-chain contracts that allow for challenging the accuracy of provided data. This involves a voting process among network participants.

5.  **Publisher SDK:** Tools and libraries to simplify the process for data providers to submit data to the oracle.

## Integration Guide

This guide outlines the steps to integrate the Canton Oracle Network into your Canton-based application.

### Prerequisites

*   A running Canton Network environment.
*   Daml SDK installed (version 3.1.0 or later).
*   Familiarity with Daml smart contract development.
*   Access to the Oracle Network's Canton domain.

### Steps

1.  **Obtain the Oracle Contract ID:** Contact the Oracle Network operator to obtain the `ContractId` of the `OracleAggregator` contract deployed on the network. This ID is crucial for interacting with the oracle.

2.  **Import the Oracle Daml Module:** Include the relevant Daml module(s) from the `canton-oracle-network` project in your Daml project's `dependencies` section of the `daml.yaml` file:

    ```yaml
    dependencies:
      - canton-oracle-network
    ```

    Then, import the necessary modules in your Daml contract:

    ```daml
    import Oracle.Aggregator -- or the specific module you need
    ```

3.  **Fetch Data from the Oracle:**  Use the `fetch` command to retrieve the `OracleAggregator` contract.  Then, exercise a choice to retrieve the current data value for a specific data feed. For example:

    ```daml
    template MyContract
      with
        oracleAggregatorCid : ContractId OracleAggregator.OracleAggregator
        me : Party
      where
        signatory me

        choice RequestData : Decimal
          controller me
          do
            oracleAggregator <- fetch oracleAggregatorCid
            value <- exercise oracleAggregatorCid OracleAggregator.GetData
              with
                dataFeedId = "EURUSD" -- Example data feed ID
            return value
    ```

    In this example:

    *   `oracleAggregatorCid` is the `ContractId` of the `OracleAggregator` contract.
    *   `GetData` is a choice on the `OracleAggregator` that allows retrieving data.
    *   `dataFeedId` is the identifier of the specific data feed you want to access (e.g., "EURUSD", "US10Y").  Available data feed IDs are defined by the Oracle Network operator.
    *   The choice returns a `Decimal` representing the aggregated data value.

4.  **Handle Data Updates:**  The Oracle Network may provide a mechanism for data consumers to be notified of updates (e.g., through events). Implement appropriate logic in your contract to handle these updates and react accordingly.

5.  **Error Handling:** Implement proper error handling in your contract to gracefully manage scenarios where data is unavailable or invalid.

### Code Example (Daml)

```daml
module MyProject.Contracts where

import Daml.Script
import Oracle.Aggregator as OracleAggregator

template MyContract
  with
    oracleAggregatorCid : ContractId OracleAggregator.OracleAggregator
    me : Party
  where
    signatory me

    choice RequestData : Decimal
      controller me
      do
        oracleAggregator <- fetch oracleAggregatorCid
        value <- exercise oracleAggregatorCid OracleAggregator.GetData
          with
            dataFeedId = "EURUSD" -- Example data feed ID
        return value

script
  testOracleIntegration = script do
    oracleAdmin <- allocateParty "OracleAdmin"
    dataProvider1 <- allocateParty "DataProvider1"
    consumer <- allocateParty "Consumer"

    -- Simplified OracleAggregator creation (replace with actual deployment logic)
    oracleAggregatorCid <- create oracleAdmin (OracleAggregator.OracleAggregator
      with
        admin = oracleAdmin
        authorizedProviders = [dataProvider1]
        dataFeedDefinitions = [ OracleAggregator.DataFeedDefinition "EURUSD" 4 ] -- Example: EURUSD with 4 decimal places
      )

    myContractCid <- create consumer (MyContract with oracleAggregatorCid = oracleAggregatorCid, me = consumer)

    eurusdValue <- exercise consumer myContractCid RequestData

    assertMsg "EURUSD value should be a Decimal" (eurusdValue > 0.0) -- Basic validation
```

### Data Provider Integration

If you are a data provider and wish to contribute to the Oracle Network, please contact the network operator. The operator will provide you with the necessary credentials and SDK to submit data securely. The Publisher SDK will handle the complexities of interacting with the Oracle contracts and ensuring data integrity.

### Dispute Resolution

If you believe that the data provided by the Oracle Network is inaccurate, you can initiate a dispute resolution process. This involves submitting a formal challenge through the designated on-chain mechanism. The network will then follow a predefined process to investigate the claim and resolve the dispute. Refer to the Oracle Network's governance documentation for details on the dispute resolution process.

## Security Considerations

*   **Access Control:** Ensure that only authorized parties can access and modify data within the Oracle Network.
*   **Data Validation:** Implement robust data validation mechanisms to prevent malicious or inaccurate data from being propagated.
*   **Smart Contract Audits:** Regularly audit the smart contracts to identify and address potential security vulnerabilities.
*   **Key Management:** Securely manage the cryptographic keys used to sign and authenticate data.

## Support

For any questions or issues regarding the Canton Oracle Network, please contact the network operator or refer to the project's documentation.