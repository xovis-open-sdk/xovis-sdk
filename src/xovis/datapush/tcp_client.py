"""
Xovis SDK - Data Plane TCP Client

This module implements a high-speed active TCP ingestion client.
It connects to Xovis sensors configured in SERVER mode (ports 49156/49159)
and extracts concatenated JSON frames using a zero-copy sliding buffer,
adhering strictly to the Data Plane's non-blocking architecture.
"""

import asyncio
import json
import logging

from xovis.datapush.sinks import XovisSink
from xovis.datapush.utils import DataPlaneIngestor

logger = logging.getLogger("xovis_sdk.tcp_client")


class XovisTCPClient:
    """
    Active TCP Ingestion Client for Xovis Telemetry.

    Initiates and persists a connection to a Xovis sensor running in SERVER mode.
    Utilizes a sliding string buffer to slice out continuous JSON payloads without
    network delimiters, routing them to attached sinks.
    """

    def __init__(self, host: str, port: int = 49156, reconnect_interval: float = 5.0):
        """
        Initializes the XovisTCPClient.

        Args:
            host (str): The IP address or hostname of the Xovis sensor.
            port (int, optional): The TCP port the sensor is listening on.
                Defaults to 49156 (Singlesensor) or 49159 (Multisensor).
            reconnect_interval (float, optional): Seconds to wait before attempting
                to reconnect after a drop. Defaults to 5.0.
        """
        self.host = host
        self.port = port
        self.reconnect_interval = reconnect_interval
        self.sinks: list[XovisSink] = []
        self._running = False

    def attach_sink(self, sink: XovisSink) -> "XovisTCPClient":
        """
        Attaches a telemetry consumer to the client.

        Args:
            sink (XovisSink): An object implementing the XovisSink protocol.

        Returns:
            XovisTCPClient: The client instance for method chaining.
        """
        self.sinks.append(sink)
        return self

    async def start(self) -> None:
        """
        Starts the client connection loop.

        Continuously attempts to connect to the sensor and read the stream.
        If the connection drops or the sensor reboots, it will automatically
        back off and reconnect.
        """
        self._running = True
        logger.info(f"Xovis TCP Client starting connection loop to {self.host}:{self.port}")

        while self._running:
            try:
                await self._connect_and_read()
            except (ConnectionRefusedError, TimeoutError, OSError) as e:
                logger.warning(f"Connection to {self.host}:{self.port} failed: {e}. Retrying in {self.reconnect_interval}s...")
            except Exception as e:
                logger.error(f"Unexpected error in TCP client for {self.host}:{self.port}: {e}")

            if self._running:
                await asyncio.sleep(self.reconnect_interval)

    async def stop(self) -> None:
        """Terminates the active connection loop."""
        self._running = False
        logger.info(f"Xovis TCP Client stopping connection to {self.host}:{self.port}")

    async def _connect_and_read(self) -> None:
        """
        Maintains the active socket and parses the byte stream.

        Uses the `raw_decode` sliding buffer to slice complete JSON objects
        out of the fragmented MTU network chunks.
        """
        reader, writer = await asyncio.open_connection(self.host, self.port)
        logger.info(f"Successfully connected to Xovis sensor at {self.host}:{self.port}")

        buffer = ""
        decoder = json.JSONDecoder()

        try:
            while self._running:
                chunk = await reader.read(8192)
                if not chunk:
                    logger.warning(f"TCP stream closed by sensor {self.host}:{self.port}")
                    break

                buffer += chunk.decode("utf-8", errors="ignore")

                while buffer:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break

                    try:
                        frame, index = decoder.raw_decode(buffer)
                        buffer = buffer[index:]

                        asyncio.create_task(DataPlaneIngestor.route_to_sinks(frame, self.sinks))

                    except json.JSONDecodeError:
                        if not buffer.startswith(("{", "[")):
                            buffer = buffer[1:]
                            continue
                        break

        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Disconnected from {self.host}:{self.port}")

