"""
Xovis SDK - Manifest Tools Generator.

Dynamically extracts the registered MCP tools from the server, serializes their
schemas, descriptions, annotations, and output schemas, and injects them directly
into `manifest.json` and `bundle_dir/manifest.json`. This ensures that Smithery's
static analyzer can discover and grade the capabilities with a perfect score.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath("src"))

from xovis.mcp.server import handle_list_tools


async def generate_manifest_tools() -> None:
    """
    Retrieves MCP tools from the server, serializes them, and updates manifest files.
    """
    print("Extracting tools from MCP server...")
    mcp_tools = await handle_list_tools()
    print(f"Extracted {len(mcp_tools)} tools.")

    serialized_tools_basic = []
    serialized_tools_full = []
    for tool in mcp_tools:
        # 1. Basic tool for top-level tools array (must have inputSchema to satisfy schema validation)
        basic_tool = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
        }
        if tool.outputSchema:
            basic_tool["outputSchema"] = tool.outputSchema
        if tool.annotations:
            annotations_dict = {}
            if hasattr(tool.annotations, "readOnlyHint") and tool.annotations.readOnlyHint is not None:
                annotations_dict["readOnlyHint"] = tool.annotations.readOnlyHint
            if hasattr(tool.annotations, "destructiveHint") and tool.annotations.destructiveHint is not None:
                annotations_dict["destructiveHint"] = tool.annotations.destructiveHint
            if annotations_dict:
                basic_tool["annotations"] = annotations_dict

        serialized_tools_basic.append(basic_tool)

        # 2. Full tool for static_responses in _meta
        full_tool = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
        }
        if tool.outputSchema:
            full_tool["outputSchema"] = tool.outputSchema
        if tool.annotations:
            annotations_dict = {}
            if hasattr(tool.annotations, "readOnlyHint") and tool.annotations.readOnlyHint is not None:
                annotations_dict["readOnlyHint"] = tool.annotations.readOnlyHint
            if hasattr(tool.annotations, "destructiveHint") and tool.annotations.destructiveHint is not None:
                annotations_dict["destructiveHint"] = tool.annotations.destructiveHint
            if annotations_dict:
                full_tool["annotations"] = annotations_dict

        serialized_tools_full.append(full_tool)

    # File paths to update
    manifest_paths = ["manifest.json", "bundle_dir/manifest.json"]

    for path in manifest_paths:
        if not os.path.exists(path):
            print(f"Warning: File not found at {path}, skipping.")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Upgrade manifest_version to 0.3 to support _meta and modern schemas
        data["manifest_version"] = "0.3"

        # Inject basic tools and tools_generated flag
        data["tools"] = serialized_tools_basic
        data["tools_generated"] = True

        # Inject _meta static responses for tools/list to expose full schemas/annotations
        if "_meta" not in data:
            data["_meta"] = {}
        if "com.microsoft.windows" not in data["_meta"]:
            data["_meta"]["com.microsoft.windows"] = {}
        if "static_responses" not in data["_meta"]["com.microsoft.windows"]:
            data["_meta"]["com.microsoft.windows"]["static_responses"] = {}

        data["_meta"]["com.microsoft.windows"]["static_responses"]["tools/list"] = {"tools": serialized_tools_full}

        # Also add under another standard namespace to make sure Smithery finds it
        # (e.g. general co.smithery.ai or just standard static responses if needed)
        if "co.smithery.ai" not in data["_meta"]:
            data["_meta"]["co.smithery.ai"] = {}
        if "static_responses" not in data["_meta"]["co.smithery.ai"]:
            data["_meta"]["co.smithery.ai"]["static_responses"] = {}

        data["_meta"]["co.smithery.ai"]["static_responses"]["tools/list"] = {"tools": serialized_tools_full}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"Successfully updated tools in {path}")


if __name__ == "__main__":
    asyncio.run(generate_manifest_tools())
