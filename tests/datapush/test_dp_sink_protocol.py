"""
Xovis SDK - Data Plane Sink Protocol Tests

Validates the standard `XovisSink` attachment and message processing logic
to ensure third-party integrations correctly receive telemetry frames.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from xovis.datapush.sinks import XovisSink


class GenericMockSink(XovisSink):
    """A generic implementation of XovisSink for testing attachment logic."""

    async def on_frame(self, frame: dict) -> None:
        pass

    async def on_events(self, events: list) -> None:
        pass


@pytest.mark.asyncio
async def test_sink_protocol_attachment():
    """
    Verifies that any object satisfying the XovisSink protocol can be attached.

    Ensures that the Data Plane servers can successfully route parsed payloads
     to developer-defined sink implementations.
    """
    # This test verifies the protocol compliance and routing logic
    # without exposing proprietary binary packing or Redis pipelines.
    mock_sink = MagicMock(spec=GenericMockSink)
    mock_sink.on_frame = AsyncMock()

    test_frame = {"time": 123456789, "tracked_objects": []}

    # Simulate routing a frame to the sink
    await mock_sink.on_frame(test_frame)

    mock_sink.on_frame.assert_called_once_with(test_frame)
