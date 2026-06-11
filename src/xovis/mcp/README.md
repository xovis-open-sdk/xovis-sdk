# Xovis SDK - Model Context Protocol (MCP) Server

This directory contains the `xovis.mcp` module, the standardized bridge for **Autonomous Desktop Agents**. It implements the Anthropic Model Context Protocol (MCP), allowing AI-native IDEs and desktop applications to orchestrate Xovis hardware natively via standard I/O.

## Architectural Intent

The MCP server transforms the Xovis SDK from a library into a **Live Resource Provider**. By exposing the `XovisAIToolkit` over a JSON-RPC 2.0 boundary, it enables agents like Claude Desktop, Cursor, and Windsurf to "attach" to a local sensor network, query topology, and execute configuration changes without requiring the agent to write and execute its own Python scripts for every interaction.

### Architectural Pillars:
1.  **Standardized Tool Projection**: Automatically maps SDK `CallablePrimitives` to MCP `Tool` definitions, including strict Pydantic-derived input schemas.
2.  **State-as-Resource**: Exposes physical device state and topology (via `HostStateBucket`) as queryable MCP Resources.
3.  **Secure Tunneling**: Leverages the SDK's `HubClient` tunnel to route MCP requests from a local developer machine through the Cloud HUB to remote edge sensors.
4.  **AI Privacy & Zero-Trust**: Inherits the `AIPrivacyFilter` and `AgentAuthorizationScope` from the `XovisAIToolkit` to ensure that desktop agents operate within a secure, sanitized sandbox.

## Components & Capabilities

### 1. The MCP Entry Point (`server.py`)
A high-performance, asynchronous server utilizing `mcp.server.stdio`. It manages the lifecycle of the JSON-RPC connection and serves as the primary dispatcher for tool calls.

### 2. Live Tool Discovery
The server dynamically inspects the `XovisAIToolkit` at runtime. Any tool registered in the toolkit is automatically projected into the MCP client's "Toolbox," complete with docstring-derived descriptions and type-safe arguments.

### 3. Safety & Privacy Guardrails
All MCP tool calls are proxied through the `XovisSafetyGuardrail`. High-impact operations (e.g., reboots) initiated via MCP **require** explicit confirmation payloads. Additionally, the integrated **AI Privacy Filter** ensures that sensitive hardware identifiers never leave the MCP transport layer, while **Authorization Scopes** restrict the agent to a whitelisted subset of the fleet.

## Deployment & Configuration

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
        "XOVIS_MCP_PASS": "password"
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
        "XOVIS_MCP_PASS": "password"
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
