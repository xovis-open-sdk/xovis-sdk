"""
Xovis SDK - Data Plane UDP Server

This module implements a high-performance UDP ingestion engine for Xovis
telemetry. It utilizes `asyncio.DatagramProtocol` for low-latency ingestion
of discrete JSON packets, residing strictly within the Data Plane.
"""

import asyncio
import logging
from typing import Optional

from xovis.datapush.sinks import XovisSink
from xovis.datapush.utils import DataPlaneIngestor

logger = logging.getLogger("xovis_sdk.udp")


class XovisUDPProtocol(asyncio.DatagramProtocol):
    """
    Protocol implementation for high-speed UDP ingestion.

    Handles incoming datagrams from Xovis sensors. Each datagram is expected
    to be a complete JSON frame. This class operates in the hot path and
    dispatches telemetry to sinks with minimal overhead.
    """

    def __init__(self, sinks: list[XovisSink]):
        """
        Initializes the UDP protocol.

        Args:
            sinks (List[XovisSink]): A list of attached telemetry sinks.
        """
        self.sinks = sinks
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        """
        Called when the UDP socket is ready.

        Args:
            transport (asyncio.DatagramTransport): The transport for the socket.
        """
        self.transport = transport
        peer = transport.get_extra_info("peername")
        logger.debug(f"UDP socket ready: {peer}")

    def datagram_received(self, data: bytes, addr: tuple):
        """
        Hot path ingestion for UDP datagrams.

        Parses the incoming byte packet as a JSON object and routes it to
        the attached sinks.

        Args:
            data (bytes): The raw packet data.
            addr (tuple): The source address of the packet.
        """
        # Check if we should log to studio debug log
        studio_debug = False
        if hasattr(self, "sinks"):
            for sink in self.sinks:
                if hasattr(sink, "debug") and sink.debug:
                    studio_debug = True
                    break

        if studio_debug:
            try:
                with open("xovis_studio_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"--- UDP datagram received from {addr}: {len(data)} bytes ---\n")
            except Exception:
                pass

        try:
            logger.debug(f"Received UDP datagram from {addr}: {len(data)} bytes")
            frame = DataPlaneIngestor.parse_frame(data)

            asyncio.create_task(DataPlaneIngestor.route_to_sinks(frame, self.sinks))

        except Exception as e:
            logger.error(f"UDP stream error from {addr}: {e}")


class XovisUDPServer:
    """
    High-performance UDP Ingestion Engine for Xovis Telemetry.

    Operates within the Data Plane to provide low-latency telemetry ingestion.
    Coordinates the lifecycle of the UDP socket and the underlying protocol.
    """

    def __init__(self):
        """
        Initializes the XovisUDPServer.
        """
        self.sinks: list[XovisSink] = []
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[XovisUDPProtocol] = None

    def attach_sink(self, sink: XovisSink) -> "XovisUDPServer":
        """
        Attaches a telemetry consumer to the server.

        Args:
            sink (XovisSink): An object implementing the XovisSink protocol.

        Returns:
            XovisUDPServer: The server instance for method chaining.
        """
        self.sinks.append(sink)
        return self

    async def stop(self):
        """
        Gracefully tears down the UDP server.
        """
        if self.transport:
            self.transport.close()
            self.transport = None
            logger.info("Xovis UDP Server stopped")

    async def start(self, host: str = "0.0.0.0", port: int = 9002):  # nosec B104
        """
        Starts the UDP server and begins listening for datagrams.

        Args:
            host (str, optional): The network interface to bind to. Defaults to "0.0.0.0".
            port (int, optional): The UDP port to listen on. Defaults to 9002.

        Raises:
            OSError: If binding fails.
        """
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(lambda: XovisUDPProtocol(self.sinks), local_addr=(host, port))
        logger.info(f"Xovis UDP Server listening on {host}:{port}")

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            if self.transport:
                self.transport.close()
            logger.info("Xovis UDP Server stopped")
