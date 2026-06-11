# Xovis SDK - The Agentic Layer

This directory contains the `xovis.skills` module, the definitive **Agentic Layer** of the Xovis SDK. It modernizes hardware orchestration by transforming physical edge sensors and Cloud HUB fleet operations into standardized, strictly validated toolsets for Large Language Models (LLMs) and autonomous agent frameworks.

## Architectural Intent

In the current state-of-the-art landscape, hardware nodes are no longer passive targets for scripts; they are intelligent participants in autonomous ecosystems. This module provides the "Universal Translator" required to bridge the gap between low-level "Layer 2" SDK logic and high-level "Layer 3" AI reasoning loops.

### Architectural Pillars:
1.  **Universal Tool Adapter (`XovisAIToolkit`)**: A dynamic schema-shifter that projects Pydantic V2 models into function-calling protocols for OpenAI, Anthropic, and LangGraph.
2.  **The Agentic Memory Plane (`XovisAgentMemory`)**: A high-density, zero-latency observation window. It provides agents with minified hardware state snapshots, eliminating the network penalty of redundant polling.
3.  **Fleet-Scale Orchestration (`XovisFleetToolkit`)**: Exposes resilient, concurrent `bulk_execute` operations as atomic tools for managing thousands of sensors via a single reasoning context.
4.  **Framework Interoperability (`LangChain Adapter`)**: Bridges the SDK's native toolkit with the LangChain ecosystem, enabling seamless integration into LangGraph cyclic reasoning loops.

## Components & Capabilities

### 1. XovisAIToolkit (Universal Adapter)
The primary entry point for both single-device and fleet-wide orchestration. It manages the complex routing of LLM tool requests to the underlying asynchronous SDK managers.

*   **OpenAI GPT-5.5 Optimized**: Generates strict JSON schemas via `get_openai_tools()`.
*   **Latest Anthropic Models Ready**: Provides the flat `input_schema` format required by the Messages API via `get_anthropic_tools()`.
*   **Callable Primitives**: Exports direct references to async functions and their validation models for **LangGraph**, **CrewAI**, and **Cursor/Windsurf**.

### 2. XovisAgentMemory (State Observation)
Autonomous agents require environmental context without the 12.5Hz network overhead. By wrapping the `HostStateBucket`, this plane allows for the injection of minified, JSON-serialized hardware "memories" directly into the System Prompt.

### 3. XovisFleetToolkit (Distributed Management)
A specialized orchestrator for `HubClient` contexts. It exposes high-impact tools such as `reboot_fleet` and `get_fleet_summary`, enabling an agent to supervise entire global deployments with fault isolation.

### 4. LangChain & Multi-Agent Adapters
Bridges the SDK's native toolkit with modern agent frameworks.
*   **LangChain**: Native `StructuredTools` for LangGraph reasoning loops.
*   **CrewAI / AutoGPT**: Dedicated adapters providing `BaseTool` abstractions for multi-agent coordination.

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

### Safety & Guardrails
The Agentic Layer includes an enterprise-grade safety engine to prevent hallucination-driven outages and accidental fleet destruction.

*   **Safety Levels**: Every tool is categorized as `OPEN`, `RESTRICTED`, `CRITICAL`, or `BLOCKED`.
*   **Hard Block (BLOCKED)**: Strictly forbids execution of specific tools. Attempting to call a blocked tool results in an immediate `PermissionError`, even if confirmation is provided.
*   **Mandatory Confirmation**: High-impact operations (e.g., `reboot_fleet`) require an explicit `confirmation=True` argument from the LLM.
*   **Execution Quotas**: Limits the number of `CRITICAL` operations allowed per session (default: 3).
*   **Agent Authorization Scope**: Defines a zero-trust boundary for multi-tenant isolation, whitelisting specific MACs, customers, groups, or tags.
*   **AI Privacy Filter**: Automatically scrubs sensitive fields (e.g., MAC addresses, IP addresses, billing data) from LLM responses using Pydantic metadata.
*   **Dynamic Restricted Tools**: Allows users to manually elevate ANY tool to `CRITICAL` or `BLOCKED` status via the `restricted_tools` dictionary.
*   **Dry Run Mode**: Allows for safe agent training by intercepting and simulating hardware-modifying commands.

#### Implementation Example (Dynamic Safety, Blocking & Scoping):
```python
from xovis.skills.toolkit import XovisAIToolkit, XovisSafetyGuardrail, AgentAuthorizationScope, SafetyLevel

# 1. Define a zero-trust authorization scope for a specific customer
scope = AgentAuthorizationScope(allowed_customers={"RetailCorp-DACH"})

# 2. Elevate an OPEN tool to CRITICAL and Hard-Block a destructive tool
guardrail = XovisSafetyGuardrail(
    authorization_scope=scope,
    restricted_tools={
        "get_system_info": SafetyLevel.CRITICAL,
        "factory_reset": SafetyLevel.BLOCKED
    }
)

# 1. get_system_info now MUST provide confirmation=True
# 2. factory_reset is now impossible for the agent to call
# 3. The agent can ONLY see/manage devices belonging to RetailCorp-DACH
toolkit = XovisAIToolkit(client, guardrail=guardrail)
```

### 6. AI Privacy Filter (Automatic Sanitization)
The `AIPrivacyFilter` utility is integrated natively into the toolkit's execution pipeline. By leveraging Pydantic V2 `json_schema_extra` metadata (`ai_privacy: BLOCK`), the SDK automatically scrubs sensitive data (tenant IDs, exact MAC addresses, private IP ranges) before they are serialized and sent to the LLM. This ensures that the agentic reasoning loop remains compliant with data residency and privacy regulations without manual intervention.

## Standards & Compliance

*   **Pydantic V2 Validation**: Every skill utilizes strict schema enforcement. Malformed LLM payloads are intercepted and rejected before they reach the hardware.
*   **Zero-Inline-Comment, Max-Docstring**: Adheres to the SDK's enterprise documentation standard. Architectural intent and Pydantic constraints are formalized exclusively through rigorous Google-style docstrings.
*   **Asynchronous Excellence**: All tools are natively non-blocking, ensuring compatibility with the high-throughput `uvloop` event loop used in the Data Plane.

---
**Note:** For edge-level resource management (Zones, Lines, Logics), refer to the `xovis.api.device.resources` documentation.
