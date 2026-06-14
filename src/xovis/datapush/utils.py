"""
Xovis SDK - Data Plane Utilities

This module provides centralized high-performance ingestion helpers for the Data Plane.
It standardizes JSON parsing via `orjson`, connection test filtering, and sink dispatching
across all transport layers (HTTP, UDP, TCP, MQTT).
"""

import asyncio
import logging
from typing import Any, Dict, List, Union

import orjson

from xovis.datapush.sinks import XovisSink

logger = logging.getLogger("xovis_sdk.datapush.utils")


class DataPlaneIngestor:
    """
    Centralized logic for telemetry ingestion and dispatching.
    """

    @staticmethod
    def parse_frame(data: Union[bytes, str]) -> Dict[str, Any]:
        """
        Standardized frame parsing with binary fallback.

        Attempts to parse the input as JSON using `orjson`. If parsing fails,
        wraps the raw bytes in a `recording_data` pseudo-frame.

        Args:
            data (Union[bytes, str]): The raw frame data.

        Returns:
            Dict[str, Any]: The parsed JSON frame or a binary fallback frame.
        """
        if not data:
            return {}

        try:
            return orjson.loads(data)
        except (orjson.JSONDecodeError, TypeError):
            # If it's already a dict (e.g. from TCP raw_decode), just return it
            if isinstance(data, dict):
                return data

            # Fallback for binary recordings
            logger.debug(f"Received non-JSON payload of {len(data)} bytes")
            return {"recording_data": data if isinstance(data, bytes) else data.encode("utf-8")}

    @staticmethod
    async def route_to_sinks(frame: Dict[str, Any], sinks: List[XovisSink]) -> None:
        """
        Standardized sink dispatching and filtering.

        Filters out connection tests and routes frames/events to all attached sinks.

        Args:
            frame (Dict[str, Any]): The parsed telemetry frame.
            sinks (List[XovisSink]): List of attached telemetry sinks.
        """
        if not frame or not sinks:
            return

        # Intercept Connection Tests
        if "connection_test" in frame:
            logger.debug("Filtered connection_test frame")
            return

        events = frame.get("events", [])
        tasks = []
        for sink in sinks:
            try:
                # Schedule both frame and event processing
                tasks.append(sink.on_frame(frame))
                if events:
                    tasks.append(sink.on_events(events))
            except Exception as e:
                logger.error(f"Error preparing sink task: {e}")

        if tasks:
            # Execute all sink tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Sink execution error: {res}")
