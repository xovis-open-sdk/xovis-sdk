"""
Xovis SDK - Data Plane TCP Server

This module implements a high-speed TCP ingestion engine for Xovis telemetry.
It handles raw concatenated JSON datapush using a sliding buffer and
`json.JSONDecoder().raw_decode()` for zero-copy extraction, adhering to the
Data Plane's throughput requirements.
"""

import asyncio
import json
import logging

from xovis.datapush.sinks import XovisSink
from xovis.datapush.utils import DataPlaneIngestor

logger = logging.getLogger("xovis_sdk")


class XovisTCPServer:
    """
    High-speed TCP Ingestion Engine for Xovis Telemetry.

    Manages persistent TCP connections from Xovis sensors. Implements a
    specialized sliding buffer to extract concatenated JSON frames without
    delimiters, dispatching them to attached sinks with minimal latency.
    """

    def __init__(self):
        """
        Initializes the XovisTCPServer.
        """
        self.sinks: list[XovisSink] = []

    def attach_sink(self, sink: XovisSink) -> "XovisTCPServer":
        """
        Attaches a telemetry consumer to the server.

        Args:
            sink (XovisSink): An object implementing the XovisSink protocol.

        Returns:
            XovisTCPServer: The server instance for method chaining.
        """
        self.sinks.append(sink)
        return self

    async def stop(self):
        """
        Gracefully tears down the TCP server.
        """
        if hasattr(self, "_server") and self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Xovis TCP Server stopped")

    async def start(self, host: str = "0.0.0.0", port: int = 9000):  # nosec B104
        """
        Starts the TCP server and begins listening for sensor connections.

        Args:
            host (str, optional): The network interface to bind to. Defaults to "0.0.0.0".
            port (int, optional): The TCP port to listen on. Defaults to 9000.

        Raises:
            OSError: If the port is already in use or binding fails.
        """
        self._server = await asyncio.start_server(self._handle_client, host, port)
        logger.info(f"Xovis TCP Server listening on {host}:{port}")
        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Handles an individual sensor connection lifecycle.

        Uses a sliding string buffer combined with `raw_decode` to safely
        extract concatenated JSON objects from the raw byte stream.

        Args:
            reader (asyncio.StreamReader): The client stream reader.
            writer (asyncio.StreamWriter): The client stream writer.
        """
        peer = writer.get_extra_info("peername")
        logger.info(f"Sensor connected: {peer}")

        # Check if we should log to studio debug log
        # We look for any attached MetricSink with debug=True
        studio_debug = False
        if hasattr(self, "sinks"):
            for sink in self.sinks:
                if hasattr(sink, "debug") and sink.debug:
                    studio_debug = True
                    break

        if studio_debug:
            try:
                with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"--- Sensor connected: {peer} ---\n")
            except Exception:
                pass

        buffer = ""
        decoder = json.JSONDecoder()

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(reader.read(8192), timeout=60.0)
                except asyncio.TimeoutError:
                    logger.debug(f"Read timeout for {peer}")
                    continue

                if not chunk:
                    logger.info(f"Connection closed by peer: {peer}")
                    break

                logger.debug(f"Received chunk from {peer}: {len(chunk)} bytes")
                buffer += chunk.decode("utf-8", errors="ignore")

                while buffer:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break

                    try:
                        frame, index = decoder.raw_decode(buffer)
                        buffer = buffer[index:]

                        # Check if the frame actually contains data we care about
                        # Some Xovis frames might be heartbeat/metadata only
                        logger.debug(f"Dispatching frame from {peer}: {list(frame.keys())}")
                        asyncio.create_task(DataPlaneIngestor.route_to_sinks(frame, self.sinks))

                    except json.JSONDecodeError:
                        # If we can't decode, it might be partial or truly malformed.
                        # To handle interleaved malformed data, we could try to skip one character and retry,
                        # but standard Xovis stream shouldn't have malformed data.
                        # However, for robustness, if it's not the start of a possible JSON object/array, we skip.
                        if not buffer.startswith(("{", "[")):
                            buffer = buffer[1:]
                            continue
                        break

        except Exception as e:
            logger.error(f"Stream error from {peer}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Sensor disconnected: {peer}")
