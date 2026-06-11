"""
Xovis SDK - Data Plane Server Compliance Validation

Validates that the native ASGI and Socket servers correctly filter out Xovis
'connection_test' health probes without forwarding them to the downstream data
pipelines (Sinks), while seamlessly processing real telemetry frames.
"""

import asyncio
import json
import logging
import socket

import httpx
import pytest

from xovis.datapush.http_server import XovisHTTPServer
from xovis.datapush.sinks import XovisSink
from xovis.datapush.tcp_server import XovisTCPServer
from xovis.datapush.udp_server import XovisUDPServer

logger = logging.getLogger(__name__)


def get_free_port() -> int:
    """Dynamically acquires a free port from the OS to prevent CI collisions."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class ComplianceSink(XovisSink):
    """Deterministic sink that signals an asyncio.Event upon frame ingestion."""

    def __init__(self):
        self.frames = []
        self.frame_received = asyncio.Event()

    async def on_frame(self, frame: dict) -> None:
        self.frames.append(frame)
        self.frame_received.set()

    async def on_events(self, events: list) -> None:
        pass


@pytest.mark.asyncio
async def test_tcp_connection_test_filtering():
    """Validates TCP socket server intercepts connection_test payloads."""
    server = XovisTCPServer()
    sink = ComplianceSink()
    server.attach_sink(sink)

    # Use port 0 for automatic OS assignment
    server_task = asyncio.create_task(server.start(host="127.0.0.1", port=0))

    # Wait for server to bind and get port
    for _ in range(20):
        if hasattr(server, "_server") and server._server and server._server.sockets:
            break
        await asyncio.sleep(0.1)
    else:
        pytest.fail("TCP Server failed to bind within timeout")

    port = server._server.sockets[0].getsockname()[1]

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)

        # 1. Send connection test (Should be filtered)
        conn_test = json.dumps({"connection_test": {"status": "ok"}})
        writer.write(conn_test.encode())
        await writer.drain()

        # 2. Send actual frame (Should trigger event)
        real_frame = json.dumps({"sensor_id": "tcp_test", "count": 1})
        writer.write(real_frame.encode())
        await writer.drain()

        writer.close()
        await writer.wait_closed()

        # Deterministic wait
        await asyncio.wait_for(sink.frame_received.wait(), timeout=2.0)

        assert len(sink.frames) == 1, "Sink received wrong number of frames"
        assert sink.frames[0]["sensor_id"] == "tcp_test"
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_udp_connection_test_filtering():
    """Validates UDP datagram server intercepts connection_test payloads."""
    server = XovisUDPServer()
    sink = ComplianceSink()
    server.attach_sink(sink)

    # Use port 0 for automatic OS assignment
    server_task = asyncio.create_task(server.start(host="127.0.0.1", port=0))

    # Wait for server to bind and get port
    port = None
    for _ in range(20):
        if hasattr(server, "transport") and server.transport:
            port = server.transport.get_extra_info("sockname")[1]
            break
        await asyncio.sleep(0.1)
    else:
        pytest.fail("UDP Server failed to bind within timeout")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 1. Send connection test
        sock.sendto(json.dumps({"connection_test": {}}).encode(), ("127.0.0.1", port))

        # 2. Send real frame
        sock.sendto(json.dumps({"sensor_id": "udp_test"}).encode(), ("127.0.0.1", port))
        sock.close()

        await asyncio.wait_for(sink.frame_received.wait(), timeout=2.0)

        assert len(sink.frames) == 1
        assert sink.frames[0]["sensor_id"] == "udp_test"
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_http_auth_and_filtering():
    """Validates HTTP ASGI server enforces Bearer Auth and filters test probes."""
    token = "strict_secret_token"
    server = XovisHTTPServer(expected_token=token)
    sink = ComplianceSink()
    server.attach_sink(sink)

    # HTTP server currently doesn't expose assigned port easily without internal access
    # So we use a dedicated test port range
    port = 9015
    server_task = asyncio.create_task(server.start(host="127.0.0.1", port=port))
    await asyncio.sleep(0.2)  # Allow aiohttp to start

    url = f"http://127.0.0.1:{port}/webhook"

    try:
        async with httpx.AsyncClient() as client:
            # 1. Test unauthorized rejection
            resp = await client.post(url, json={"data": "none"})
            assert resp.status_code == 401

            # 2. Test authorized connection test (200 OK, but no sink forward)
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(url, json={"connection_test": {}}, headers=headers)
            assert resp.status_code == 200
            assert not sink.frame_received.is_set()

            # 3. Test authorized real frame
            resp = await client.post(url, json={"sensor_id": "http_test"}, headers=headers)
            assert resp.status_code == 200

        await asyncio.wait_for(sink.frame_received.wait(), timeout=2.0)

        assert len(sink.frames) == 1
        assert sink.frames[0]["sensor_id"] == "http_test"
    finally:
        await server.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
