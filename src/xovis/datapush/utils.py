"""
Xovis SDK - Data Plane Ingestion Utilities

This module provides high-performance, centralized utilities for telemetry
ingestion across all transport layers (HTTP, UDP, TCP, MQTT). It standardizes
JSON parsing, binary data handling, connection test filtering, and sink routing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Union

import orjson

from xovis.datapush.sinks import XovisSink

logger = logging.getLogger("xovis_sdk.datapush.utils")


class DataPlaneIngestor:
    """
    Centralized Ingestion Logic for the Data Plane.

    Standardizes how telemetry data is parsed and routed to sinks, ensuring
    consistent behavior across all transport protocols while maintaining
    maximum performance.
    """

    @staticmethod
    def parse_frame(data: Union[bytes, str]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parses raw telemetry data into a JSON-compatible structure.

        Uses `orjson` for high-performance deserialization. If parsing fails,
        the raw data is wrapped in a `recording_data` frame to support binary
        recording ingestion.

        Args:
            data (Union[bytes, str]): The raw telemetry data received from a sensor.

        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: The parsed JSON frame(s)
                or a wrapped binary fallback frame.
        """
        if isinstance(data, str):
            data = data.encode("utf-8", errors="ignore")

        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError:
            # Binary fallback for non-JSON payloads (e.g., sensor recordings)
            logger.debug("Non-JSON payload received, falling back to binary wrapping.")
            return {"recording_data": data}

    @staticmethod
    async def route_to_sinks(frame: Dict[str, Any], sinks: List[XovisSink]) -> None:
        """
        Routes a parsed telemetry frame to all attached sinks.

        Filters out connection tests and heartbeats before dispatching to sinks.
        Handles both single frames and lists of frames (batched payloads).

        Args:
            frame (Dict[str, Any]): The parsed telemetry frame.
            sinks (List[XovisSink]): A list of sinks to receive the telemetry.
        """
        if not sinks:
            return

        # Handle batching (if frame is actually a list of frames)
        if isinstance(frame, list):
            for f in frame:
                await DataPlaneIngestor.route_to_sinks(f, sinks)
            return

        # Centralized Connection Test Filtering
        if "connection_test" in frame:
            logger.debug("Filtered out connection_test frame")
            return

        # Unified routing to sinks
        tasks = []
        for sink in sinks:
            try:
                # Primary telemetry channel
                tasks.append(asyncio.create_task(sink.on_frame(frame)))

                # Secondary event-specific channel (if implemented by sink)
                if "events" in frame and hasattr(sink, "on_events"):
                    tasks.append(asyncio.create_task(sink.on_events(frame["events"])))

            except Exception as e:
                logger.error(f"Error routing to sink {sink}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
