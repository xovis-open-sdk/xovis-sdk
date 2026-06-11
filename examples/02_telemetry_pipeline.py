"""
Xovis SDK - Telemetry Pipeline Example

Demonstrates the high-speed Data Plane ingestion pipeline, including diagnostic
logging and custom sink attachment for raw spatial coordinate processing.
Operates within the Data Plane.
"""

import asyncio
import logging
import os
from typing import Any

from xovis.datapush.sinks import XovisSink
from xovis.datapush.tcp_server import XovisTCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xovis-telemetry")


class ConsoleAnalyticsSink(XovisSink):
    """
    A generic diagnostic sink that processes high-level telemetry frames.
    Demonstrates the extensible Open Core plugin architecture of the Data Plane.
    In a production environment, this is where proprietary Layer 3 logic
    is implemented.
    """

    async def on_frame(self, frame: dict[str, Any]) -> None:
        # Extract tracked objects natively without locking the event loop
        objects = frame.get("tracked_objects", [])
        if objects:
            logger.info(f"Processed Frame: {len(objects)} active tracks in field of view.")

    async def on_events(self, events: list[dict[str, Any]]) -> None:
        """Logs triggered sensor events (e.g., Zone entries)."""
        for event in events:
            logger.info(f"Event Triggered: {event.get('type')} (Track: {event.get('track_id')})")


async def main():
    # 1. Configuration
    host = os.getenv("XOVIS_SINK_HOST", "0.0.0.0")
    port = int(os.getenv("XOVIS_SINK_PORT", 9000))

    # 2. Instantiate the High-Speed Ingestion Server
    # The SDK supports XovisTCPServer, XovisHTTPServer (Webhooks), and XovisUDPServer (Datagrams).
    # On Linux/macOS, this automatically leverages uvloop for maximum throughput.
    server = XovisTCPServer()

    # 3. Attach Sinks
    # Attach our custom console analytics sink
    # Developers implement their own proprietary sinks by inheriting from XovisSink
    server.attach_sink(ConsoleAnalyticsSink())

    # 4. Start the Data Plane Server
    # This block is non-blocking and processes massive concurrent sensor datapush via sliding string buffers
    logger.info(f"Starting Data Plane Pipeline on {host}:{port}...")
    try:
        await server.start(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")


if __name__ == "__main__":
    asyncio.run(main())
