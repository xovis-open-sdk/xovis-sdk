"""
Xovis SDK - Data Plane Sink Interfaces

This module defines the architectural contract for all telemetry consumers
within the Data Plane. It provides the `XovisSink` protocol, ensuring a
unified interface for high-frequency frame and event processing.
"""

import logging
from typing import Protocol

try:
    import orjson as json
except ImportError:
    pass

logger = logging.getLogger("xovis_sdk")


class XovisSink(Protocol):
    """
    Base interface for developer integrations attaching to the stream.

    Defines the standard protocol for processing incoming telemetry data.
    Implementations of this protocol are attached to `XovisTCPServer`,
    `XovisUDPServer`, or `XovisHTTPServer` to receive real-time updates.
    """

    async def on_frame(self, frame: dict) -> None:
        """
        Triggered for every tracked frame received from the sensor.

        In standard configurations, this occurs approximately 12.5 times per
        second and contains all tracked objects and coordinates.

        Args:
            frame (dict): The parsed telemetry frame payload.
        """
        ...

    async def on_events(self, events: list) -> None:
        """
        Triggered when discrete events are detected by the sensor.

        Captures high-level logic events such as zone entries, exits, or
        line crossings.

        Args:
            events (list): A list of discrete event dictionaries.
        """
        ...
