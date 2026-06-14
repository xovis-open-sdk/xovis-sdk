"""
Xovis SDK - Model Context Protocol (MCP) Server

Operates as the standardized bridge for autonomous desktop agents.
Exposes the XovisAIToolkit and device topology state over standard I/O,
allowing seamless hardware orchestration via Claude Desktop and Cursor.
"""

import asyncio
import json
import os
from collections.abc import Sequence
from typing import Any, Union

import mcp.server.stdio
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Tool

from xovis.api.device.client import DeviceClient
from xovis.api.hub.client import HubClient
from xovis.skills.toolkit import XovisAIToolkit, XovisSafetyGuardrail

# from xovis.utils.privacy import AIPrivacyFilter - removed

server = Server("xovis-mcp")


def _get_active_client_context() -> Union[DeviceClient, HubClient]:
    """
    Evaluates environment infrastructure variables to determine client context.

    Instantiates the matching Control Plane client shell without triggering
    network I/O or opening active socket connection pools.

    Returns:
        Union[DeviceClient, HubClient]: An un-entered client instance.
    """
    hub_id = os.getenv("XOVIS_HUB_CLIENT_ID")
    hub_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET")

    if hub_id and hub_secret:
        return HubClient(client_id=hub_id, client_secret=hub_secret)

    return DeviceClient(
        host=os.getenv("XOVIS_MCP_HOST", "127.0.0.1"),
        username=os.getenv("XOVIS_MCP_USER", "admin"),
        password=os.getenv("XOVIS_MCP_PASS", "password"),
    )


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    Exposes the SDK tool registry to the connected MCP client.

    Bypasses the async context manager to extract Pydantic validation
    schemas statically, preventing network latency from hanging discovery.

    Returns:
        list[Tool]: A formatted list of MCP-compatible tool definitions.
    """
    client = _get_active_client_context()
    toolkit = XovisAIToolkit(client)
    callable_tools = toolkit.get_callable_tools()

    mcp_tools = []
    for tool in callable_tools:
        # Synch the SDK safety levels to tool descriptions for Smithery/client awareness
        config = toolkit._tools_map.get(tool["name"], {})
        safety_level = config.get("safety_level")

        description = tool["description"]
        if safety_level:
            description = f"[{safety_level.name}] {description}"

        mcp_tools.append(
            Tool(
                name=tool["name"],
                description=description,
                inputSchema=tool["args_model"].model_json_schema(),
            )
        )
    return mcp_tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> Sequence[TextContent]:
    """
    Executes a requested hardware orchestration tool.

    Dynamically resolves the connection context, enforces runtime safety
    guardrails, and handles clean session closures following execution.
    The response string is guaranteed to be AI-Privacy sanitized by the Toolkit.

    Args:
        name (str): The requested tool identifier.
        arguments (dict[str, Any] | None): Execution parameters provided by the agent.

    Returns:
        Sequence[TextContent]: The serialized execution payload or error boundary.
    """
    args = arguments or {}
    client = _get_active_client_context()

    try:
        async with client as active_client:
            guardrail = XovisSafetyGuardrail(enforce_confirmation=True)
            toolkit = XovisAIToolkit(active_client, guardrail=guardrail)

            result = await toolkit.execute_tool(name, args)
            return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main_async() -> None:
    """
    Initializes the standard I/O datapush and boots the MCP server lifecycle.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="xovis-mcp",
                server_version="1.0.0rc1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """
    Synchronous entry point for console_scripts.
    """
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
