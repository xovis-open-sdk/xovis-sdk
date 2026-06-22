"""
Xovis SDK - Model Context Protocol (MCP) Server

Operates as the standardized bridge for autonomous desktop agents.
Exposes the XovisAIToolkit and device topology state over standard I/O,
allowing seamless hardware orchestration via Claude Desktop and Cursor.
"""

import asyncio
import hashlib
import json
import os
import re
from collections.abc import Sequence
from typing import Any, Union

import mcp.server.stdio
from dotenv import load_dotenv
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Tool, ToolAnnotations

from xovis.api.device.client import DeviceClient
from xovis.api.hub.client import HubClient
from xovis.mcp.formatters import mcp_safe_serializer
from xovis.skills.toolkit import XovisAIToolkit, XovisSafetyGuardrail

working_dir_env = os.path.join(os.getcwd(), ".env")
if os.path.exists(working_dir_env):
    load_dotenv(dotenv_path=working_dir_env)
else:
    load_dotenv()

server = Server("xovis-mcp")

_GLOBAL_CLIENT: Union[DeviceClient, HubClient] | None = None


def _get_active_client_context() -> Union[DeviceClient, HubClient]:
    """Evaluates environment infrastructure variables to determine client context.

    Instantiates the matching Control Plane client shell without triggering
    network I/O or opening active socket connection pools.

    Returns:
        Union[DeviceClient, HubClient]: An un-entered client instance.
    """

    def clean_env(key: str, default: str = "") -> str:
        val = os.getenv(key, default)
        if val:
            return val.strip("'\" ")
        return val

    hub_id = clean_env("XOVIS_HUB_CLIENT_ID")
    hub_secret = clean_env("XOVIS_HUB_CLIENT_SECRET")

    if hub_id and hub_secret:
        return HubClient(client_id=hub_id, client_secret=hub_secret)

    return DeviceClient(
        host=clean_env("XOVIS_MCP_HOST", "127.0.0.1"),
        username=clean_env("XOVIS_MCP_USER", "admin"),
        password=clean_env("XOVIS_MCP_PASS", "password"),
    )


def _normalize_schema(schema: Any) -> Any:
    """
    Recursively normalizes Pydantic JSON schemas to strict Draft 7 format required by Anthropic/Smithery.
    Strips 'anyOf' and enforces strict 'type' parameters.
    """
    if isinstance(schema, dict):
        if "anyOf" in schema:
            types = []
            for sub in schema.pop("anyOf"):
                if isinstance(sub, dict) and "type" in sub:
                    if isinstance(sub["type"], list):
                        types.extend(sub["type"])
                    else:
                        types.append(sub["type"])
            if types:
                types = list(set(types))
                if "string" in types and "integer" in types:
                    schema["type"] = "string"
                else:
                    schema["type"] = types[0] if len(types) == 1 else types

        # Ensure all object properties have a type if they are properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for prop_name, prop_val in schema["properties"].items():
                if isinstance(prop_val, dict):
                    if "type" not in prop_val and "anyOf" not in prop_val and "$ref" not in prop_val:
                        prop_val["type"] = "object"

        # Recurse into all dictionary values
        for key, value in list(schema.items()):
            schema[key] = _normalize_schema(value)

        # Clean up types after recursion
        if isinstance(schema.get("type"), list):
            types = [t for t in schema["type"] if t != "null"]
            if types:
                schema["type"] = types[0]

    elif isinstance(schema, list):
        for i, item in enumerate(schema):
            schema[i] = _normalize_schema(item)

    return schema


def _to_mcp_name(original_name: str) -> str:
    """Translates an internal tool name to a clean 3-part dot-notation tree structure.

    Args:
        original_name (str): The raw, snake_case tool name within the SDK toolkit.

    Returns:
        str: A dot-notated tool name matching 'xovis.<category>.<action>'.
    """
    custom_mappings = {
        "get_system_info": "xovis.system.get_info",
        "get_agent_memory": "xovis.system.get_memory",
        "get_fleet_summary": "xovis.fleet.get_summary",
        "reboot_fleet": "xovis.fleet.reboot",
    }
    if original_name in custom_mappings:
        return custom_mappings[original_name]

    if original_name.startswith("aggregate_"):
        action = original_name[len("aggregate_") :]
        return f"xovis.aggregate.{action}"

    for category in ["system", "network", "analytics", "privacy", "datapush", "scene", "history", "update", "users", "itxpt"]:
        if original_name.startswith(f"{category}_"):
            action = original_name[len(f"{category}_") :]
            return f"xovis.{category}.{action}"

    return f"xovis.{original_name.replace('_', '.', 1)}"


def _from_mcp_name(mcp_name: str) -> str:
    """Reverses the clean dot-notation tree structure back to the original SDK tool name.

    Args:
        mcp_name (str): The dot-notated MCP tool identifier.

    Returns:
        str: The matching internal SDK tool name.
    """
    reverse_mappings = {
        "xovis.system.get_info": "get_system_info",
        "xovis.system.get_memory": "get_agent_memory",
        "xovis.fleet.get_summary": "get_fleet_summary",
        "xovis.fleet.reboot": "reboot_fleet",
    }
    if mcp_name in reverse_mappings:
        return reverse_mappings[mcp_name]

    if mcp_name.startswith("xovis.aggregate."):
        action = mcp_name[len("xovis.aggregate.") :]
        return f"aggregate_{action}"

    for category in ["system", "network", "analytics", "privacy", "datapush", "scene", "history", "update", "users", "itxpt"]:
        prefix = f"xovis.{category}."
        if mcp_name.startswith(prefix):
            action = mcp_name[len(prefix) :]
            return f"{category}_{action}"

    name = mcp_name
    if name.startswith("xovis."):
        name = name[6:]
    return name.replace(".", "_", 1)


_SANITIZED_TO_ORIGINAL: dict[str, str] = {}


def _has_proprietary_access() -> bool:
    """Checks whether proprietary visual SDK resources are present in the environment."""
    try:
        from xovis.api.device.resources import images_private

        return True
    except ImportError:
        return False


def sanitize_mcp_tool_name(name: str) -> str:
    """Enforces strict Anthropic MCP tool name regex and deterministic 64-char length limits."""
    # Replace anything not a-zA-Z0-9_- with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    if len(sanitized) > 64:
        # Deterministically truncate and append shake_128 hash
        h = hashlib.shake_128(name.encode("utf-8")).hexdigest(4)
        sanitized = f"{sanitized[:55]}_{h}"
    return sanitized


async def _populate_tool_maps() -> None:
    """Populates the sanitized-to-original tool name mapping context."""
    global _SANITIZED_TO_ORIGINAL
    if not _SANITIZED_TO_ORIGINAL:
        try:
            toolkit = XovisAIToolkit(_GLOBAL_CLIENT)
            for tool in toolkit.get_callable_tools():
                mcp_name = _to_mcp_name(tool["name"])
                sanitized_name = sanitize_mcp_tool_name(mcp_name)
                _SANITIZED_TO_ORIGINAL[sanitized_name] = tool["name"]
        except Exception:
            pass


@mcp_safe_serializer
async def _execute_and_serialize_tool(toolkit: XovisAIToolkit, tool_name: str, args: dict[str, Any]) -> str:
    """Invokes the toolkit executor and applies the formatting & pagination safety decorator."""
    return await toolkit.execute_tool(tool_name, args)


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Exposes the SDK tool registry to the connected MCP client."""
    toolkit = XovisAIToolkit(_GLOBAL_CLIENT)
    callable_tools = toolkit.get_callable_tools()

    await _populate_tool_maps()

    mcp_tools = []
    has_prop = _has_proprietary_access()
    for tool in callable_tools:
        config = toolkit._tools_map.get(tool["name"], {})
        safety_level = config.get("safety_level")

        description = tool["description"]
        read_only = False
        destructive = False
        if safety_level:
            description = f"[{safety_level.name}] {description}"
            if safety_level.name == "OPEN":
                read_only = True
            elif safety_level.name in ("CRITICAL", "RESTRICTED", "BLOCKED"):
                destructive = True

        raw_schema = tool["args_model"].model_json_schema()
        normalized_schema = _normalize_schema(raw_schema)

        mcp_name = _to_mcp_name(tool["name"])

        if not has_prop:
            if mcp_name in ("xovis.system.get_led", "xovis.network.get_ipv4", "xovis.analytics.get_counter"):
                continue

        sanitized_name = sanitize_mcp_tool_name(mcp_name)

        mcp_tools.append(
            Tool(
                name=sanitized_name,
                description=description,
                inputSchema=normalized_schema,
                annotations=ToolAnnotations(readOnlyHint=read_only, destructiveHint=destructive),
            )
        )

    limit = int(os.getenv("XOVIS_MCP_TOOL_LIMIT", "90"))
    if limit > 0 and len(mcp_tools) > limit:
        meta_tools = ["xovis_search_tools", "xovis_get_tool_schema", "xovis_execute_tool"]
        prioritized = [t for t in mcp_tools if t.name in meta_tools]
        others = [t for t in mcp_tools if t.name not in meta_tools]
        mcp_tools = prioritized + others[: max(0, limit - len(prioritized))]

    return mcp_tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> Sequence[TextContent]:
    """Executes a requested hardware orchestration tool."""
    import logging

    args = arguments or {}

    await _populate_tool_maps()
    original_name = _SANITIZED_TO_ORIGINAL.get(name) or _from_mcp_name(name)

    if original_name == "execute_tool" and "tool_name" in args:
        inner_name = args["tool_name"]
        args["tool_name"] = _SANITIZED_TO_ORIGINAL.get(inner_name) or _from_mcp_name(inner_name)

    logging.info(f"Tool called: {original_name} with arguments: {args}")

    try:
        guardrail = XovisSafetyGuardrail(enforce_confirmation=True)
        toolkit = XovisAIToolkit(_GLOBAL_CLIENT, guardrail=guardrail)

        result = await _execute_and_serialize_tool(toolkit, original_name, args)
        logging.info(f"Tool {original_name} completed successfully.")
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logging.error(f"Error executing tool {original_name}: {str(e)}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main_async() -> None:
    """
    Initializes the standard I/O datapush and boots the MCP server lifecycle.
    """
    global _GLOBAL_CLIENT

    # Establish a persistent client connection to reuse HTTPX connection pooling.
    client_context = _get_active_client_context()
    async with client_context as active_client:
        _GLOBAL_CLIENT = active_client
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="xovis-mcp",
                    server_version="1.0.0a29",
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
    import argparse
    import logging

    parser = argparse.ArgumentParser(description="Xovis MCP Server")
    parser.add_argument("--log-file", type=str, help="Optional log file path.")
    args = parser.parse_args()

    if args.log_file:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(args.log_file)],
        )
        logging.info("MCP Server starting...")

    asyncio.run(main_async())


if __name__ == "__main__":
    main()
