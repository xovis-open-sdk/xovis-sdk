# Model Context Protocol (MCP)

| **Status** | **Discovery** | **Installation** |
|:---:|:---:|:---:|
| [![Smithery Verified](https://smithery.ai/badge/xovis-sdk/xovis-mcp)](https://smithery.ai/servers/xovis-sdk/xovis-mcp) | [![MCP Ready](https://img.shields.io/badge/MCP-Ready-5B32A8.svg?logo=server&logoColor=white)](https://modelcontextprotocol.io/) | [![Smithery Install](https://img.shields.io/badge/Smithery-Install-orange.svg)](https://smithery.ai/server/xovis-sdk) |

The `xovis.mcp` module is the standardized bridge for **Autonomous Desktop Agents**. It implements the Anthropic Model Context Protocol (MCP), allowing AI-native IDEs and desktop applications to orchestrate Xovis hardware natively via standard I/O.

## Architectural Intent

The MCP server transforms the Xovis SDK from a library into a **Live Resource Provider**. By exposing the `XovisAIToolkit` over a JSON-RPC 2.0 boundary, it enables agents like Claude Desktop, Cursor, and Windsurf to "attach" to a local sensor network, query topology, and execute configuration changes without requiring the agent to write and execute its own Python scripts for every interaction.

### Architectural Pillars:

1.  **Standardized Tool Projection**: Automatically maps SDK `CallablePrimitives` to MCP `Tool` definitions, including strict Pydantic-derived input schemas.
2.  **State-as-Resource**: Exposes physical device state and topology (via `HostStateBucket`) as queryable MCP Resources.
3.  **Secure Tunneling**: Leverages the SDK's `HubClient` tunnel to route MCP requests from a local developer machine through the Cloud HUB to remote edge sensors.

## Components & Capabilities

### 1. The MCP Entry Point (`server.py`)
A high-performance, asynchronous server utilizing `mcp.server.stdio`. It manages the lifecycle of the JSON-RPC connection and serves as the primary dispatcher for tool calls.

### 2. Live Tool Discovery
The server dynamically inspects the `XovisAIToolkit` at runtime. Any tool registered in the toolkit is automatically projected into the MCP client's "Toolbox," complete with docstring-derived descriptions and type-safe arguments.

### 3. Safety Guardrails
All MCP tool calls are proxied through the `XovisSafetyGuardrail`. High-impact operations (e.g., reboots) initiated via MCP **require** explicit confirmation payloads, preventing accidental hardware outages during agentic reasoning loops.

## Prerequisites: Type Generation

Before using the MCP server, you MUST generate the local resource types. The MCP server relies on these types to provide the AI with accurate autocompletion for resource IDs (e.g., Zone names, Line IDs, MAC addresses).

1.  **Warmup**: Run `xovis-cli warmup --host <DEVICE_IP>` to sync hardware state.
2.  **Generate Types**: Run `xovis-cli generate-types` to create the `xovis_types.py` definitions.

For a detailed explanation of the type generation system and the CLI commands, see the [CLI Documentation](../cli.md#generate-types).

## Deployment & Configuration {: #deployment-configuration }

To ensure seamless cross-platform execution on Windows, macOS, and Linux, the MCP server is optimized to run using portable execution entry points instead of machine-specific absolute file paths.

### Portable Entry Points

- **Option A (Interactive IDEs / Virtual Environments)**: Use the python module-based invocation `python -m xovis.mcp.server`. This ensures that the active Python environment's path resolution is automatically respected across all shells (PowerShell, Bash, Zsh).
- **Option B (System-wide Command)**: Use the registered global executable `xovis-mcp` defined in the package scripts.

### Dynamic Environment Loading (.env)

The server automatically scans for and loads `.env` configuration files in the current working directory relative to execution, allowing credentials like `XOVIS_MCP_HOST` to be managed modularly.

### Tool Limits & Execution Workaround

Some AI agents (like Claude or Cursor) impose a strict maximum on the number of tools they can consume (typically 40-100). The Xovis MCP Server natively provides over 260 tools. To prevent clients from rejecting the connection, the MCP Server uses an optional tool limit configurable via the `XOVIS_MCP_TOOL_LIMIT` environment variable (defaults to 90).

When the limit is active, the server selectively exposes a subset of tools, prioritizing the following three meta-tools:
1. `xovis_search_tools`: Search for hidden tools.
2. `xovis_get_tool_schema`: Retrieve the JSON schema for a hidden tool.
3. `xovis_execute_tool`: Execute any tool, even if it is not exposed in the limited list.

To disable the limit entirely and expose all tools, set `XOVIS_MCP_TOOL_LIMIT=0`.

### IDE Integration (Cursor / Windsurf)
To enable native hardware control within your AI-native IDE, add the following to your configuration:

```json
{
  "mcpServers": {
    "xovis": {
      "command": "python",
      "args": ["-m", "xovis.mcp.server"],
      "env": {
        "XOVIS_MCP_HOST": "10.0.0.50",
        "XOVIS_MCP_USER": "admin",
        "XOVIS_MCP_PASS": "password",
        "XOVIS_HUB_CLIENT_ID": "Optional: For Cloud Hub",
        "XOVIS_HUB_CLIENT_SECRET": "Optional: For Cloud Hub",
        "XOVIS_MCP_TOOL_LIMIT": "90"
      }
    }
  }
}
```

### Claude Desktop Integration
Add the Xovis MCP server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "xovis": {
      "command": "xovis-mcp",
      "env": {
        "XOVIS_MCP_HOST": "127.0.0.1",
        "XOVIS_MCP_USER": "admin",
        "XOVIS_MCP_PASS": "password",
        "XOVIS_MCP_TOOL_LIMIT": "90"
      }
    }
  }
}
```

## Standards & Compliance

*   **MCP 1.0.0+ Compatible**: Adheres to the latest Model Context Protocol specification.
*   **JSON-RPC 2.0**: Uses standard I/O for transport, ensuring zero-latency communication with the host agent.
*   **Zero-Inline-Comment, Max-Docstring**: Documentation is embedded within the code to ensure that the MCP server remains self-describing for the agents that connect to it.

---
**Note:** The MCP server requires the `mcp` Python package. Install it via `pip install xovis-sdk[mcp]`.
