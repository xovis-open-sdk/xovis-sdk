"""
Xovis SDK - Tier 3: Data Plane TCP Raw Parsing Tests

Validates the high-speed TCP ingestion engine's ability to handle
concatenated JSON streams without newlines or length prefixes using
the specialized sliding buffer and JSONDecoder.raw_decode().
"""

import asyncio
import json

import pytest

from xovis.datapush.sinks import XovisSink
from xovis.datapush.tcp_server import XovisTCPServer


class MockSink(XovisSink):
    """Testing sink to capture parsed frames."""

    def __init__(self):
        self.frames = []
        self.event = asyncio.Event()

    async def on_frame(self, frame: dict) -> None:
        self.frames.append(frame)
        if len(self.frames) >= 3:
            self.event.set()

    async def on_events(self, events: list) -> None:
        pass


@pytest.mark.asyncio
async def test_tcp_raw_sliding_buffer_parsing():
    """
    Asserts that concatenated JSON frames are correctly sliced and dispatched.
    """
    server = XovisTCPServer()
    sink = MockSink()
    server.attach_sink(sink)

    # Start server on a random port
    # Use a background task but we need to be able to stop it
    server_task = asyncio.create_task(server.start(host="127.0.0.1", port=0))

    # Give the server a moment to start and get the assigned port
    for _ in range(10):
        if hasattr(server, "_server"):
            break
        await asyncio.sleep(0.1)

    if not hasattr(server, "_server"):
        pytest.fail("Server failed to start")

    port = server._server.sockets[0].getsockname()[1]

    try:
        # Connect a mock sensor
        reader, writer = await asyncio.open_connection("127.0.0.1", port)

        # Prepare concatenated JSON payload (no newlines)
        # We send it in fragments to test the sliding buffer logic
        frame1 = {"id": 1, "data": "first"}
        frame2 = {"id": 2, "data": "second"}
        frame3 = {"id": 3, "data": "third"}

        raw_payload = json.dumps(frame1) + json.dumps(frame2) + json.dumps(frame3)

        # Send in two chunks, splitting frame2 in the middle
        split_idx = len(json.dumps(frame1)) + 5
        writer.write(raw_payload[:split_idx].encode())
        await writer.drain()
        await asyncio.sleep(0.1)

        writer.write(raw_payload[split_idx:].encode())
        await writer.drain()

        # Wait for all frames to be processed
        await asyncio.wait_for(sink.event.wait(), timeout=5.0)

        assert len(sink.frames) == 3
        assert sink.frames[0]["id"] == 1
        assert sink.frames[1]["id"] == 2
        assert sink.frames[2]["id"] == 3

        writer.close()
        await writer.wait_closed()

    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
