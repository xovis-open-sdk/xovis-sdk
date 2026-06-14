"""
Xovis SDK - Data Plane HTTP Server

This module implements a high-performance ASGI Webhook Server for Xovis telemetry
ingestion. It resides strictly within the Data Plane, utilizing `aiohttp` and `orjson`
for zero-copy, lock-free processing of incoming HTTP pushes without Pydantic overhead.
"""

import asyncio
import base64
import logging

import orjson
from aiohttp import web

from xovis.datapush.sinks import XovisSink
from xovis.datapush.utils import DataPlaneIngestor

logger = logging.getLogger("xovis_sdk.http")


class XovisHTTPServer:
    """
    High-performance ASGI Webhook Server for Xovis Telemetry.

    Operates strictly within the Data Plane to ingest 12.5Hz telemetry via HTTP
    webhooks. Designed for maximum throughput, it bypasses UTF-8 decoding and
    Pydantic validation, dispatching parsed frames to attached sinks via
    asynchronous fire-and-forget tasks.
    """

    def __init__(self, expected_token: str = None, expected_user: str = None, expected_password: str = None):
        self.sinks: list[XovisSink] = []
        self.expected_token = expected_token
        self.expected_user = expected_user
        self.expected_password = expected_password
        self._app = web.Application()

        # Intercept all paths to prevent 404s when the sensor drops the URI path
        self._app.router.add_route("*", "/{tail:.*}", self._handle_post)

        self._runner = None
        self._site = None

    def attach_sink(self, sink: XovisSink) -> "XovisHTTPServer":
        """
        Attaches a telemetry consumer to the server.

        Args:
            sink (XovisSink): An object implementing the XovisSink protocol
                to receive ingested telemetry frames.

        Returns:
            XovisHTTPServer: The server instance for method chaining.
        """
        self.sinks.append(sink)
        return self

    async def start(self, host: str = "0.0.0.0", port: int = 9001):  # nosec B104
        """
        Initializes the aiohttp runner and binds the TCP socket.

        Enters a non-blocking sleep loop to keep the server alive until cancelled.

        Args:
            host (str, optional): The network interface to bind to. Defaults to "0.0.0.0".
            port (int, optional): The TCP port to listen on. Defaults to 9001.

        Raises:
            OSError: If the port is already in use or binding fails.
        """
        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()
        logger.info(f"Xovis HTTP Server listening on http://{host}:{port}/webhook")

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """
        Gracefully tears down the HTTP server and cleans up active connections.
        """
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

    async def _handle_post(self, request: web.Request) -> web.Response:
        """
        Hot path ingestion for incoming HTTP requests.

        Directly reads bytes from the socket buffer and performs instantaneous
        C-level deserialization via orjson. Broadcasts frames to sinks
        asynchronously to unblock the HTTP response immediately.

        Args:
            request (web.Request): The incoming aiohttp request.

        Returns:
            web.Response: A 200 OK response on success, or appropriate error codes.
        """
        if self.expected_token:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.lower().startswith("bearer ") or auth_header[7:].strip() != self.expected_token:
                return web.Response(status=401, text="Unauthorized: Invalid Bearer Token")

        if self.expected_user and self.expected_password:
            auth_header = request.headers.get("Authorization", "")
            expected_b64 = base64.b64encode(f"{self.expected_user}:{self.expected_password}".encode()).decode("utf-8")
            if not auth_header.lower().startswith("basic ") or auth_header[6:].strip() != expected_b64:
                return web.Response(status=401, text="Unauthorized: Invalid Basic Auth")

        try:
            body_bytes = await request.read()

            if not body_bytes:
                return web.Response(status=200, text="OK")

            frame_data = DataPlaneIngestor.parse_frame(body_bytes)

            # Support firmware batching (Logics payloads are sometimes arrays)
            frames = frame_data if isinstance(frame_data, list) else [frame_data]

            for frame in frames:
                asyncio.create_task(DataPlaneIngestor.route_to_sinks(frame, self.sinks))

            return web.Response(status=200, text="OK")

        except Exception as e:
            logger.error(f"HTTP stream error: {e}")
            return web.Response(status=500, text="Internal Server Error")

