#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Set

import websockets
from websockets.server import WebSocketServerProtocol

# --- Configuration ---
# Load configuration from environment variables for production-readiness.
HOST = os.getenv("ORACLE_PUBLISHER_HOST", "localhost")
PORT = int(os.getenv("ORACLE_PUBLISHER_PORT", 8765))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
PROVIDER_NAME = os.getenv("ORACLE_PROVIDER_NAME", "CantonOracleNode-Alpha")

# --- Global State ---
# A shared set to store all connected WebSocket clients.
CONNECTED_CLIENTS: Set[WebSocketServerProtocol] = set()

# --- Logging Setup ---
# Configure structured logging for better observability.
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OraclePublisherWebsocket")


async def register_client(websocket: WebSocketServerProtocol):
    """
    Registers a new client connection and adds it to the global set.
    """
    CONNECTED_CLIENTS.add(websocket)
    logger.info(f"Client connected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    try:
        await websocket.send(json.dumps({
            "type": "status",
            "message": "Connection successful. Awaiting price updates."
        }))
    except websockets.exceptions.ConnectionClosed:
        logger.warning(f"Failed to send welcome message to {websocket.remote_address}; connection closed immediately.")


async def unregister_client(websocket: WebSocketServerProtocol):
    """
    Unregisters a client connection, removing it from the global set.
    """
    CONNECTED_CLIENTS.discard(websocket)
    logger.info(f"Client disconnected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")


async def broadcast_message(message: str):
    """
    Broadcasts a JSON message to all connected clients concurrently.
    """
    if not CONNECTED_CLIENTS:
        return

    # Use asyncio.gather to send messages to all clients in parallel.
    tasks = [client.send(message) for client in CONNECTED_CLIENTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log any errors that occurred during the broadcast.
    # The connection_handler's finally block is responsible for cleanup.
    for websocket, result in zip(list(CONNECTED_CLIENTS), results):
        if isinstance(result, Exception):
            logger.warning(f"Error sending message to client {websocket.remote_address}: {result}")


async def price_feed_generator():
    """
    Simulates a real-time price feed, generating and broadcasting updates.

    In a real system, this function would connect to upstream data sources
    (e.g., Bloomberg, Reuters, internal pricing engines) via their APIs.
    """
    # Sample instruments covering FX, Equities, Crypto, and Rates
    instruments = [
        # FX
        ("EUR/USD", 1.0850, 0.0002),
        ("GBP/USD", 1.2710, 0.0003),
        ("USD/JPY", 157.25, 0.05),
        # Equities
        ("AAPL", 191.00, 0.50),
        ("MSFT", 425.00, 0.85),
        ("NVDA", 121.00, 1.20), # Post-split price
        # Crypto
        ("BTC/USD", 67500.00, 150.0),
        ("ETH/USD", 3500.00, 45.0),
        # Rates / Treasury Yields
        ("US10Y", 4.25, 0.005)
    ]

    logger.info(f"Price feed generator started for provider: {PROVIDER_NAME}")

    while True:
        try:
            # Pick a random instrument to generate an update for.
            instrument_id, base_price, volatility = random.choice(instruments)

            # Simulate a small, random price movement.
            price_change = random.uniform(-volatility, volatility) * (1 + random.random())
            new_price = base_price + price_change

            # Construct the standardized price update payload.
            payload = {
                "type": "price_update",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "provider": PROVIDER_NAME,
                "instrumentId": instrument_id,
                "price": f"{new_price:.6f}", # Ensure consistent decimal precision
            }

            message = json.dumps(payload)
            logger.debug(f"Broadcasting update: {message}")
            await broadcast_message(message)

            # Wait for a short, variable interval to simulate a real-time stream.
            await asyncio.sleep(random.uniform(0.05, 0.8))

        except Exception as e:
            logger.error(f"Error in price feed generator: {e}", exc_info=True)
            # Avoid a tight loop on persistent errors.
            await asyncio.sleep(5)


async def connection_handler(websocket: WebSocketServerProtocol, path: str):
    """
    Manages the lifecycle of a single client WebSocket connection.
    """
    await register_client(websocket)
    try:
        # This loop keeps the connection alive. It exits when the client disconnects.
        # This publisher is primarily one-way, but we can handle incoming messages
        # for pings, subscription requests, etc., in a more advanced version.
        async for message in websocket:
            logger.info(f"Received message from {websocket.remote_address} on path '{path}': {message}")
            # Here you could handle client-side pings or subscription logic
            pass
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed for {websocket.remote_address}: code={e.code}, reason='{e.reason}'")
    except Exception as e:
        logger.error(f"Unexpected error on connection {websocket.remote_address}: {e}", exc_info=True)
    finally:
        # Ensure cleanup happens regardless of how the connection was terminated.
        await unregister_client(websocket)


async def main():
    """
    Main coroutine to set up and run the WebSocket server.
    """
    # Start the price feed generator as a background task.
    logger.info("Starting price feed generator task...")
    asyncio.create_task(price_feed_generator())

    # Start the WebSocket server.
    logger.info(f"Starting WebSocket server on ws://{HOST}:{PORT}")
    async with websockets.serve(connection_handler, HOST, PORT):
        # Server runs indefinitely until the process is stopped.
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down gracefully.")
    except Exception as e:
        logger.critical("Server failed to start or encountered a fatal error.", exc_info=True)
        exit(1)