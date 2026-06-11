"""
Xovis SDK - MQTT Data Plane Tests

Validates the MQTT client's ability to subscribe to telemetry datapush
and dispatch frames to sinks. Utilizes mocking to simulate the MQTT
broker for CI/CD compliance.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xovis.datapush.mqtt_client import XovisMQTTClient
from xovis.datapush.sinks import XovisSink


@pytest.fixture
def mock_mqtt_message():
    """Simulates a raw MQTT message from a Xovis sensor."""
    message = MagicMock()
    message.topic = "xovis/telemetry/sensor1"
    message.payload = json.dumps(
        {
            "timestamp": 1700000000,
            "element": "sensor",
            "frame": 1234,
            "events": [{"type": "ZONE_ENTRY", "zone": "Entrance"}],
        }
    ).encode("utf-8")
    return message


class MockSink(XovisSink):
    """Compliance sink for capturing MQTT frames."""

    def __init__(self):
        self.received_frames = []
        self.received_events = []

    async def on_frame(self, frame: dict) -> None:
        self.received_frames.append(frame)

    async def on_events(self, events: list) -> None:
        self.received_events.append(events)


@pytest.mark.asyncio
async def test_mqtt_client_ingestion(mock_mqtt_message):
    """
    Validates that the MQTT client correctly parses payloads and
    routes them to attached sinks.
    """
    sink = MockSink()
    # Fixed: Passing topic as it's a required positional arg in __init__
    client = XovisMQTTClient(host="localhost", topic="xovis/telemetry/#", port=1883)
    client.attach_sink(sink)

    # Mock the aiomqtt.Client
    with patch("aiomqtt.Client") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # We need an ASYNC iterator for `async for message in client.messages`
        class AsyncIterator:
            def __init__(self, items):
                self.items = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self.items)
                except StopIteration:
                    raise StopAsyncIteration

        mock_client.messages = AsyncIterator([mock_mqtt_message])

        # Run the listener in a way we can stop it
        try:
            # Fixed: client.start() no longer takes 'topic' argument
            await asyncio.wait_for(client.start(), timeout=0.2)
        except (asyncio.TimeoutError, StopIteration, StopAsyncIteration):
            pass

        # Give time for background tasks to complete
        await asyncio.sleep(0.1)

    assert len(sink.received_frames) == 1
    assert sink.received_frames[0]["frame"] == 1234
    assert len(sink.received_events) == 1
    assert sink.received_events[0][0]["type"] == "ZONE_ENTRY"


@pytest.mark.asyncio
async def test_mqtt_client_malformed_json():
    """Ensures the MQTT client gracefully handles malformed payloads."""
    sink = MockSink()
    # Fixed: Passing topic
    client = XovisMQTTClient(host="localhost", topic="xovis/telemetry/#")
    client.attach_sink(sink)

    bad_message = MagicMock()
    bad_message.payload = b"NOT_JSON"

    with patch("aiomqtt.Client") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        class AsyncIterator:
            def __init__(self, items):
                self.items = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self.items)
                except StopIteration:
                    raise StopAsyncIteration

        mock_client.messages = AsyncIterator([bad_message])

        try:
            await asyncio.wait_for(client.start(), timeout=0.1)
        except (asyncio.TimeoutError, StopIteration, StopAsyncIteration):
            pass

    # Sink should be empty
    assert len(sink.received_frames) == 0
