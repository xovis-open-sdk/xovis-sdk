# Agentic Layer (Skills)

| **Discovery** | **Installation** |
| :---: | :---: |
| [![MCP Ready](https://img.shields.io/badge/MCP-Ready-5B32A8.svg?logo=server&logoColor=white)](https://modelcontextprotocol.io/) | [![Smithery Install](https://img.shields.io/badge/Smithery-Install-orange.svg)](https://smithery.ai/server/xovis-sdk)  |

| **Compatibility** | **Frameworks** | **Optimized For** |
| :---: | :---: | :---: |
| [![OpenAI Compatible](https://img.shields.io/badge/OpenAI-Compatible-412991.svg?logo=openai&logoColor=white)](https://openai.com/) | [![LangGraph Ready](https://img.shields.io/badge/LangGraph-Ready-1C3C3C.svg?logo=langchain&logoColor=white)](https://langchain.com/) | [![Cursor Optimized](https://img.shields.io/badge/Cursor-Optimized-000000.svg?logo=python&logoColor=white)](https://cursor.sh/) |
| [![Anthropic Compatible](https://img.shields.io/badge/Anthropic-Compatible-D2B8A3.svg?logo=anthropic&logoColor=black)](https://www.anthropic.com/) | [![CrewAI Ready](https://img.shields.io/badge/CrewAI-Ready-FF4B4B.svg?logo=google-cloud&logoColor=white)](https://crewai.com/) | |

The `xovis.skills` module is the definitive **Agentic Layer** of the Xovis SDK. It modernizes hardware orchestration by transforming physical edge sensors and Cloud HUB fleet operations into standardized, strictly validated toolsets for Large Language Models (LLMs) and autonomous agent frameworks.

!!! info "Advanced Integration"
    If you are building complex agentic systems or need to understand the deep technical rules for tool-calling and safety, refer to the [Detailed Agent Instructions](../contributing/agent_instructions.md).

## Architectural Intent

In the current state-of-the-art landscape, hardware nodes are no longer passive targets for scripts; they are intelligent participants in autonomous ecosystems. This module provides the "Universal Translator" required to bridge the gap between low-level SDK logic and high-level business logic AI reasoning loops.

### Architectural Pillars:

1.  **Universal Tool Adapter (`XovisAIToolkit`)**: A dynamic reflection engine that crawls SDK managers at runtime, projecting Google-style docstrings and Pydantic V2 schemas for OpenAI, Anthropic, and LangGraph.
2.  **The Agentic Memory Plane (`XovisAgentMemory`)**: A high-density, zero-latency observation window. It provides agents with minified hardware state snapshots, eliminating the network penalty of redundant polling.
3.  **Fleet-Scale Orchestration (`XovisFleetToolkit`)**: Exposes resilient, concurrent `bulk_execute` operations as atomic tools for managing thousands of sensors via a single reasoning context.
4.  **Adaptive Pacing Engine**: Built-in congestion control that automatically adjusts request delays (0.2s for LAN, 1.0s for Cloud) to respect WAF limits and prevent hardware saturation.
5.  **Framework Interoperability (`LangChain Adapter`)**: Bridges the SDK's native toolkit with the LangChain ecosystem, enabling seamless integration into LangGraph cyclic reasoning loops.

## Components & Capabilities

### 1. XovisAIToolkit (Universal Adapter) {: #1-xovisantoolkit-universal-adapter }
The primary entry point for both single-device and fleet-wide orchestration. It manages the complex routing of LLM tool requests to the underlying asynchronous SDK managers.

*   **Dynamic Reflection Engine**: Crawls SDK managers at runtime using `inspect`, generating high-fidelity Pydantic schemas from Google-style docstrings and coroutine signatures.
*   **OpenAI GPT-5.5 Optimized**: Generates strict JSON schemas via `get_openai_tools()`.
*   **Latest Anthropic Models Ready**: Provides the flat `input_schema` format required by the Messages API via `get_anthropic_tools()`.
*   **Callable Primitives**: Exports direct references to async functions and their validation models for **LangGraph**, **CrewAI**, and **Cursor/Windsurf**.
*   **Dynamic Adapter Registry**: Allows custom or third-party framework adapters (e.g., LlamaIndex, AutoGen) to be registered via `toolkit.register_adapter(name, func)` and dynamically retrieved using `toolkit.get_tools(name)`. Standard built-in adapters (`langchain` and `crewai`) are pre-registered and lazy-loaded by default.
*   **Tool Limit & Meta-Tooling Engine**: Automatically caps exposed tools (configurable via `XOVIS_MCP_TOOL_LIMIT`, default 90) to respect strict client constraints (e.g., Cursor, Claude Desktop), while providing meta-tools (`execute_tool`, `search_tools`, `get_tool_schema`) to dynamically access the full 260+ tool registry.

### 2. XovisAgentMemory (State Observation)
Autonomous agents require environmental context without the high-frequency Live-Push overhead. By wrapping the `HostStateBucket`, this plane allows for the injection of minified, JSON-serialized hardware "memories" directly into the System Prompt.

### 3. XovisFleetToolkit (Distributed Management)
A specialized orchestrator for `HubClient` contexts. It exposes high-impact tools such as `fleet_reboot` and `get_fleet_summary`, enabling an agent to supervise entire global deployments with fault isolation.

### 4. LangChain & Multi-Agent Adapters
Bridges the SDK's native toolkit with modern agent frameworks.

*   **LangChain**: Native `StructuredTools` for LangGraph reasoning loops. Retrieved dynamically via `toolkit.get_tools("langchain")`.
*   **CrewAI / AutoGPT**: Dedicated adapters providing `BaseTool` abstractions for multi-agent coordination. Retrieved dynamically via `toolkit.get_tools("crewai")`.
*   **Custom Frameworks**: Users can register custom adapters natively on the toolkit using `toolkit.register_adapter(name, func)`.

## Integration & Implementation

### LLM Provider Support Matrix

| Provider | Method | Format |
| :--- | :--- | :--- |
| **OpenAI** | `get_openai_tools()` | Nested `{"type": "function", ...}` |
| **Anthropic** | `get_anthropic_tools()` | Flat `{"name", "description", "input_schema"}` |
| **LangChain** | `get_langchain_tools()` | List of `StructuredTool` objects |
| **CrewAI** | `get_crewai_tools()` | List of `BaseTool` objects |
| **LangGraph** | `get_callable_tools()` | List of `{"name", "callable", "args_model"}` |
| **Cursor / IDEs**| `get_callable_tools()` | Direct function primitives |

### 5. Token-Optimized Memory
The `XovisAgentMemory.get_compressed_state()` method implements a state-of-the-art compression algorithm that strips empty collections and default hardware values, reducing context window tokens by up to 40% for massive fleet summaries.

### Safety & Guardrails {: #safety-guardrails }
The Agentic Layer includes an enterprise-grade safety engine to prevent hallucination-driven outages and accidental fleet destruction. It classifies operations into four distinct safety levels (`OPEN`, `RESTRICTED`, `CRITICAL`, `BLOCKED`) and enforces strict human-in-the-loop validation, adaptive pacing, and stateful pseudonymization.

**Deep Dive:** Want to learn how the SDK prevents accidental fleet outages or secure customer metadata? Read the complete [Safety & Guardrails Guide](safety_guardrails.md).

## Standards & Compliance

*   **Pydantic V2 Validation**: Every skill utilizes strict schema enforcement. Malformed LLM payloads are intercepted and rejected before they reach the hardware.
*   **Zero-Inline-Comment, Max-Docstring**: Adheres to the SDK's enterprise documentation standard. Architectural intent and Pydantic constraints are formalized exclusively through rigorous Google-style docstrings.
*   **Asynchronous Excellence**: All tools are natively non-blocking, ensuring compatibility with the high-throughput `uvloop` event loop used in the Data Plane.

---
**Note:** For edge-level resource management (Zones, Lines, Logics), refer to the `xovis.api.device.resources` documentation.

