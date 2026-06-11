"""
Xovis SDK - DataPush Test Fixtures
"""

import asyncio

import pytest_asyncio

from xovis.datapush.http_server import XovisHTTPServer
from xovis.datapush.tcp_server import XovisTCPServer
from xovis.datapush.udp_server import XovisUDPServer


@pytest_asyncio.fixture(scope="function")
async def tcp_server():
    """
    Fixture providing a running XovisTCPServer.
    """
    server = XovisTCPServer()
    task = asyncio.create_task(server.start(host="0.0.0.0", port=9000))
    # Give it a moment to start
    await asyncio.sleep(0.1)
    try:
        yield server
    finally:
        await server.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest_asyncio.fixture(scope="function")
async def udp_server():
    """
    Fixture providing a running XovisUDPServer.
    """
    server = XovisUDPServer()
    task = asyncio.create_task(server.start(host="0.0.0.0", port=9002))
    # Give it a moment to start
    await asyncio.sleep(0.1)
    try:
        yield server
    finally:
        await server.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest_asyncio.fixture(scope="function")
async def http_server():
    """
    Fixture providing a running XovisHTTPServer.
    """
    server = XovisHTTPServer()
    task = asyncio.create_task(server.start(host="0.0.0.0", port=9001))
    # Give it a moment to start
    await asyncio.sleep(0.1)
    try:
        yield server
    finally:
        await server.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
