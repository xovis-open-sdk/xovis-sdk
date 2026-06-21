# The Control Plane (Configuration Management)

The Control Plane manages low-frequency REST API wrappers for configuring the Xovis HUB Cloud and local edge sensors.

## Unified Device Routing Layer (`UnifiedDeviceClient`)

To solve issues where the Xovis HUB does not contain real local LAN IPs (e.g., behind gateways or NAT), the SDK introduces a **Multi-Plane Hybrid Routing Strategy** via the `UnifiedDeviceClient`. 

When connecting to a device:

1.  **Local Handshake Check:** The client performs a fast TCP/HTTP probe of local IP addresses (either cached or discovered).
2.  **Direct LAN Execution:** If reachable, a direct, low-latency `DeviceClient` connection is used.
3.  **HUB Proxy Fallback:** If the local path is blocked or the device is remote, the SDK automatically falls back to spawning a secure connection routed through the Cloud HUB proxy tunnel (`HubClient.connect_device`).

---

## Control Flow and Router Diagram

```mermaid
graph TD
    subgraph "Application Layer"
        DevCode[Developer / SDK Scripts]
    end

    subgraph "Control Plane Core"
        subgraph "Clients"
            HC[HubClient]
            DC[DeviceClient]
            Smart[UnifiedDeviceClient]
        end

        subgraph "Core Utilities & Safeguards"
            Guardrail[XovisSafetyGuardrail]
            Pydantic[Pydantic V2 Model Validation]
            Probe[Proactive Capability Cache]
            TimeNorm[XovisTime Utility]
        end
    end

    subgraph "Target Hardware / Cloud"
        Hub[Xovis HUB Cloud]
        Edge[Edge Sensor / REST API]
    end

    DevCode -->|1. Normalize Time| TimeNorm
    DevCode -->|2. Serialize Payload| Pydantic
    Pydantic -->|3. Check Safety| Guardrail
    Guardrail -->|4. Probe Features| Probe
    
    Probe -->|Route Request| Smart
    Smart -->|Direct LAN Check| DC
    Smart -->|Secure Fallback Tunnel| HC
    
    DC -->|HTTP REST API v5 / httpx| Edge
    HC -->|Secure Tunnel Proxy / httpx| Edge
    HC -->|Hub APIs / httpx| Hub
```
---

## Core Philosophy

While the Data Plane prioritizes high throughput and zero blocking, the Control Plane prioritizes structural robustness, strict schema validation, security, and networking resilience.

*   **Rule - Robustness:** We use `httpx` for async networking, and `tenacity` for rate-limit (HTTP 429) and server-error (HTTP 50x) backoffs.
*   **Rule - Strict Pydantic CRUD:** All resource managers (Analytics, Scene, DataPush, etc.) MUST enforce strict schema validation using the auto-generated Pydantic V2 models. Never use raw `Dict[str, Any]` in method signatures for payloads.
*   **Rule - Pydantic Serialization:** The SDK handles Pydantic serialization natively at the `XovisHTTPClient` layer. It is hardcoded to use `exclude_unset=True` and `by_alias=True` for all Pydantic models. This is a HARD RULE to prevent `PATCH` and `PUT` requests from overwriting edge configurations with unset fields.
    *   **Context-Aware Serialization:**
        *   **Standard Usage:** Pass raw Pydantic models directly to Resource Managers or the MCP Toolkit.
        *   **Internal SDK / Bypass:** The global `request` wrapper handles serialization automatically, ensuring consistent `exclude_unset=True` and `by_alias=True` behavior.
        *   **Data Plane:** NEVER use Pydantic in the hot path. Use raw `json`/`orjson`.
*   **Rule - Proactive Hardware Probing:** Do not rely on brittle `try...except` blocks for missing hardware features. Use the lazy, asynchronous `_probe_capability` cache or license-aware checks. Note that Xovis sensors return 403 HTML (mapped to `EndpointNotFoundError`) for missing/restricted endpoints.
*   **Rule - Hub Auth0:** The Xovis Hub uses Auth0. Token requests MUST be sent as a form-encoded POST (`data={...}`, NOT `json={...}`) to `https://login.xovis.cloud/oauth/token` including the `"audience": "https://api.xovis.cloud/"` parameter. Tokens MUST be cached to disk to prevent 429 rate-limiting.
