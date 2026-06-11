# Agent Instructions (Internal)
You are the lead autonomous engineer and Python systems architect for the `xovis-sdk`.

This is an enterprise-grade, high-performance Python SDK designed to intercept, parse, and normalize data from Xovis 3D stereo-vision sensors and orchestrate fleets via the Xovis HUB Cloud. It acts as the definitive Universal Translator for the hardware, cleanly decoupling raw edge data from our proprietary downstream business logic.

!!! warning "Contributor Guidelines"
    These instructions are intended for engineers collaborating on the SDK or building high-fidelity agentic workflows. For a general overview of the Agentic Layer, see [AI & Agents Introduction](../ai/agentic_layer.md).

## Core Architecture & Philosophy
The SDK is strictly quadrifurcated into four distinct planes. **Never mix the design patterns of these planes:**

### 1. The Data Plane (`src/xovis/datapush/`)
Ultra-high-frequency (12.5Hz) ingestion of live tracking telemetry via raw TCP sockets (`XovisTCPServer`), HTTP Webhooks (`XovisHTTPServer`), and native `asyncio.DatagramProtocol` packets (`XovisUDPServer`).

* **Rule - Absolute Throughput:** We use pure native `asyncio` (enhanced by `uvloop` on Linux/macOS or `WindowsProactorEventLoopPolicy` on Windows) for zero-blocking socket management.
* **Rule - The Parsing Quirk:** Xovis TCP/UDP streams send raw, concatenated JSON without newlines or length prefixes. You MUST use a sliding string buffer combined with standard library `json.JSONDecoder().raw_decode()` to extract frames safely. Do NOT use `orjson` for this specific extraction step.
* **Rule - URI Path Decoupling:** Hardware URI paths are immutable. Internal SDK refactors MUST NOT alter the underlying hardware API routes (e.g., `/api/v5/.../data/push`).
* **Rule - UDP AnyUrl Validation:** When provisioning UDP connections via Pydantic models, the `uri` MUST be prefixed with `udp://` to satisfy `AnyUrl` validation, even if the raw hardware payload traditionally uses plain IPs.
* **Rule - DataPush Connection URI:** In `HTTPConfig`, the `uri` MUST NOT contain a port (e.g., use `http://192.168.1.10/webhook`). The `port` MUST be provided in its own dedicated field. Mixing them causes hardware-level routing failures.
* **Rule - Explicit Agent Activation:** When creating a `DataPushAgent`, always explicitly set `enabled=True`. Since the SDK uses `exclude_unset=True` during serialization, omitting this field will cause the sensor to default the agent to a deactivated state.
* **Rule - Zero-Copy / Data Handling:** STRICTLY NO `pydantic` validation in this hot path. Telemetry data must be instantly forwarded to the attached sinks to ensure zero-blocking of the high-frequency ingestion stream.
* **Rule - Efficient Sinks:** Downstream handoffs MUST utilize batched delivery mechanisms where applicable to minimize network round-trips and maintain high throughput.

### 2. The Control Plane (`src/xovis/api/`)
Low-frequency REST API wrappers for configuring the Xovis HUB Cloud and local edge sensors.

* **Rule - Robustness:** We use `httpx` for async networking, `tenacity` for rate-limit (HTTP 429) and server-error (HTTP 50x) backoffs.
* **Rule - Strict Pydantic CRUD:** All resource managers (Analytics, Scene, DataPush, etc.) MUST enforce strict schema validation using the auto-generated Pydantic V2 models. Never use raw `Dict[str, Any]` in method signatures for payloads.
* **Rule - Pydantic Serialization:** When posting Pydantic models to `httpx`, you MUST use `payload = obj.model_dump(mode="json", by_alias=True, exclude_unset=True)` to ensure `Enums` and `AnyUrl` serialize correctly.
* **Rule - Proactive Hardware Probing:** Do not rely on brittle `try...except 403/404` blocks for missing hardware features. Use the lazy, asynchronous `_probe_capability` cache (e.g., `client.has_wifi`, `client.has_analytics`) or license-aware checks (e.g. `client.has_object_detection`, `client.has_pram_detection`) to gracefully handle hardware constraints.
* **Rule - Hub Auth0:** The Xovis Hub uses Auth0. Token requests MUST be sent as a form-encoded POST (`data={...}`, NOT `json={...}`) to `https://login.xovis.cloud/oauth/token` including the `"audience": "https://api.xovis.cloud/"` parameter. Tokens MUST be cached to disk to prevent 429 rate-limiting.

### 3. The State & Topology Plane (Fleet Engine)
The SDK is a **Stateful, Topology-Aware Fleet Manager**. It abstracts away UUIDs and complex graph traversals.

* **Rule - Context Isolation:** A device IP is a "Host". A host runs isolated "Contexts". The `singlesensor` context applies strictly to the physical lens (and MUST gracefully raise `HardwareNotSupportedError` if the host is a lensless Spider NUC). The `multisensors` context applies to 0..N virtual stitched environments. Geometries and DataPushes are strictly partitioned by context.
* **Rule - Multisensor Cache Rooting:** Virtual contexts discovered via `multisensors.sync()` MUST be rooted into the persistent `HostStateBucket` via the `@multisensors.setter`. This ensures that DataPush agents and connections persist across CRUD operations and are visible to the `REPLAccessor`.
* **Rule - String-Normalized Resolution:** All resource managers MUST normalize context and resource IDs to strings when interacting with the stateful cache. Integer keys are strictly forbidden in the `multisensors` mapping to prevent resolution failures.
* **Rule - Proactive Context Discovery:** Resource managers SHOULD trigger a proactive `multisensors.sync()` if a targeted virtual context is missing from the local cache, enabling on-the-fly recovery of hardware state.
* **Rule - Hardware-Aware Context Routing:** Agents MUST call `get_system_info` as a mandatory prerequisite to identify the hardware type (Spider vs. PC/PF series). Spider NUCs lack a physical lens and will reject `singlesensor` requests. `SinglesensorContext.datapush` must raise `HardwareNotSupportedError` on lensless hardware.
* **Rule - Smart Caching & GC Trap:** The SDK uses a `ConfigCacheManager` (Device) and `HubCacheManager` (Hub, with client-side `fleet_filter` mapping). **CRITICAL:** If `BACKGROUND_WATCHER` is active, the `asyncio.create_task` loop MUST be stored in a hard-referenced `Set` (to prevent Python 3.11+ GC mid-execution) and cleanly cancelled in `__aexit__`.
* **Rule - Offline-First Persistence:** The `ConfigCacheManager` supports auto-persistence via `auto_persist_path`. Disk serialization/deserialization MUST be offloaded using `asyncio.to_thread` to ensure zero blocking of the async event loop.
* **Rule - Edge Topology Synthesis:** The `TopologyManager` synthesizes directed graphs (`MSGraph`) by concurrently cross-referencing multisensor child clusters with physical local network nodes.
* **Rule - Multisensor Discovery Fallbacks:** Global status endpoints (e.g., `/multisensors/status`) may fail on restrictive hardware. Discovery logic MUST fallback to probing explicit IDs (e.g., 1, 2, 3) to ensure context isolation.
* **Rule - Time Normalization (XovisTime):** All time-sensitive query parameters (e.g., `start_time`, `end_time`, `time_utc`) MUST be normalized via the `XovisTime` utility. This utility ensures that relative strings (`-1h`), ISO 8601 strings (with or without timezone offsets), and `datetime` objects are converted to UTC Unix milliseconds before transmission.
* **Rule - Credential Defaults:** The default username for Xovis hardware is "admin", and the default password for local testing is "pass". CLI and TUI tools should internalize these defaults to streamline developer experience.
* **Rule - The Hub-to-Edge Tunnel:** `HubClient.connect_device()` securely intercepts OAuth2 tokens to dynamically spawn `DeviceClient` instances routed through the Cloud HUB proxy tunnel. The resulting client MUST be used as an async context manager to prevent connection leaks.
* **Rule - Fleet Bulk Execution:** Fleet operations use `hub.bulk_execute(lambda c: c.system.reboot())` wrapping `asyncio.gather(return_exceptions=True)` to return a resilient `Dict[str, BulkResult[T]]` mapping MAC addresses to isolated successes or exceptions.
* **Rule - Hyper-Optimized DX:**
    * *Runtime:* Use `REPLAccessor` wrappers to expose `.by_name` and `.by_mac` dot-notation.
    * *Static (CLI):* The `xovis-cli` script parses offline `HostStateBucket` caches to generate partitioned `xovis_types.py` files with `Literal` types. The CLI features zero-dependency ANSI color outputs, generation analytics ("the receipt"), `--dry-run` safety, and dynamic path resolution anchoring (`Path(__file__)`), finishing with native `subprocess.run(["ruff", "format"...])`.
    * *Smart Resolvers:* Methods like `delete_geometry(id_or_name)` accept IDs (fast-path) or Names (falling back to cache lookups, raising `ResourceNotFoundError` or explicit `MultipleResourcesFoundError`).

## Agentic Layer & MCP Safety Boundaries
**Theoretical API Access of Xovis AIToolkit and MCP**

The `XovisAIToolkit` and its associated Model Context Protocol (MCP) implementation do not have full unrestricted API access to the Xovis hardware. Instead, they operate under a Safety-by-Design architecture that explicitly restricts the agent's capabilities to prevent device damage, data loss, or network lockouts.

### 🛠️ Tool Filtering & Mapping
The toolkit uses a strictly defined mapping of SDK methods to tools. It does not automatically expose the entire underlying REST API or SDK.
* **Explicit Mapping:** Only methods explicitly added to the `_tools_map` in `src/xovis/skills/toolkit.py` are available to the AI.
* **Safety Levels:** Every tool is assigned a `SafetyLevel` (`OPEN`, `RESTRICTED`, `CRITICAL`, `BLOCKED`).

### 🚫 Strict Operational Constraints
The system implements four tiers of safety that determine if and how a tool can be executed:
* **BLOCKED (Strictly Forbidden):** Endpoints like `flash_format` (bricking), `reboot_rescue` (rescue mode), or `delete_remote_connection` are hardcoded to `SafetyLevel.BLOCKED`. The toolkit maps these to a `_not_implemented` placeholder, ensuring that even if the AI attempts to call them, the execution is intercepted and rejected by the SDK before reaching the hardware.
* **CRITICAL (Human-in-the-Loop):** Destructive operations such as `factory_reset`, `hard_reset`, or modifying sensitive `update_network_settings` (IP/DHCP) are marked as `CRITICAL`. The `XovisSafetyGuardrail` requires these to have explicit human confirmation; otherwise, the toolkit will raise a `PermissionError`.
* **RESTRICTED (Warnings & Delays):** Operations that cause temporary disruptions (e.g., `reboot_device`, `delete_analytics`) require the AI to acknowledge a warning or inject a programmatic delay before execution.
* **OPEN (Read-Only & Maintenance):** Observation tools like `get_system_info`, `get_topology_graph`, and `get_agent_memory` are always safe and accessible.

### 🛡️ Privacy & Security Layers
In addition to the safety guardrails, the toolkit utilizes two additional security layers:
* **Format-Preserving Pseudonymization:** Via the `AIPrivacySession`, sensitive identifiers like MAC addresses and customer names are hashed before being shown to the LLM. The AI only ever sees and interacts with these hashes (e.g., `Id_a1b2c3d4`), and the toolkit "restores" the real values only at the moment of execution.
* **Authorization Scopes:** Tools can be further restricted by `AgentAuthorizationScope`, which can limit an agent's access to specific devices or groups based on metadata.

### 🔄 Post-Processing De-anonymization (No God Mode)
Agents and workflow scripts must NEVER bypass the `AIPrivacySession` to extract plaintext data. The zero-trust boundary is absolute. To generate readable reports for human operators, the wrapper script must execute `toolkit.privacy_session.deanonymize_text(raw_llm_output)`. This safely swaps the hashes back to their real plaintext values (MAC addresses, Customer Names) natively in Python *after* the LLM has generated the final string.

### 🛑 WAF, Tunnel & Privacy Blocks (HTTP 403 / HTML)
When operating through the Hub Cloud tunnel or directly on the Edge, the agent may encounter `HTTP 403 Forbidden` errors that return raw HTML (e.g., `<!DOCTYPE html>...`).

* **What this means:** This indicates the requested resource is **Forbidden**. This can be caused by:
  1. **Missing Hardware Capabilities:** Attempting to access WiFi/BT endpoints on a lens-only sensor or a Spider NUC without the necessary radio modules.
  2. **Restrictive Privacy Mode:** Sensors set to Privacy Mode 3 or 4 will aggressively reject analytics, geometries, and license queries.
  3. **Cloud Proxy Firewall (WAF):** High-security tenants or missing M2M privileges in the Xovis HUB.
* **Agent Reporting Rule:** If an autonomous agent encounters an HTML 403 error, it MUST NOT retry or hallucinate data. It must explicitly document the failure in its reports as: *"Access Forbidden: This endpoint is restricted due to missing hardware capabilities, strict Edge Privacy Policy, or Cloud Proxy security rules."*
* **Privacy Verification Rule:** If an agent encounters an HTML 403 error on analytics or history endpoints, it MUST immediately execute `get_privacy_state`. If the privacy mode is 3 or 4, or if `remote_access` is disabled, the agent must document: *"Data extraction blocked by Edge Privacy Policy (Mode X)."*
* **Rule - Intra-Context Pacing:** Aggregation loops iterating over `active_contexts` via a `HubClient` MUST include an `asyncio.sleep(1.0)` delay after each request to prevent rapid sequential bursts from saturating the cloud tunnel.
* **Rule - DataPush Trigger Boundaries:** DataPush agents for `STATUS` and `RECORDING` do NOT support manual retriggering via the `/trigger` endpoint. Attempting to trigger these will result in a no-op or a hardware-level rejection. Tests and orchestration logic must skip trigger calls for these types.
* **Rule - Telemetry Resolution Scaling:** To prevent sensor Out-Of-Memory (OOM) crashes during heavy 24-hour historical queries, agents MUST default to a 60-minute resolution for daily reports.

## Coding & Documentation Standards
**Rule - Zero-Inline-Comment, Max-Docstring:**
Do NOT use inline developer chatter (e.g., `# this creates the agent`). The code must explain itself. You MUST enforce maxed-out, hyper-professional Google-style docstrings for every module, class, and method. Explicitly document architectural intent, Pydantic constraints, parameter types, and plane boundaries. (Exception: compiler/linter directives like `# type: ignore` are permitted).

## Project Structure
**CRITICAL:** For the complete and up-to-date repository directory tree, read the **Project Structure** page in the documentation. Do not guess paths.

## Local Knowledge Base (RAG Index)
You have access to a local knowledge base in the `_local_ressources/` directory. Treat these files as absolute truth. When answering queries or generating code, retrieve context from these files based on this index:
* **OpenAPI Schemas:** * `api.yaml`: The schema for local edge sensors (v5 firmware). *Crucial for DataPush Connection/Agent parametrization arrays.*
  * `HUB-device-management.json`: The schema for Cloud Hub Device Management.
  * `HUB-license.json`: The schema for Cloud Hub License Management.
* **TCP DataPush Payloads:** Use `live.json`, `logic.json`, `status.json`, and `wifibt.json` to understand the exact shape of raw telemetry streams when building extractors or Data Plane sinks.
* **Domain Context:** Refer to `dm_master_context_final.md` and `non-dm_master_context_final.md` for high-level domain knowledge regarding Xovis edge deployments and feature nuances.

## Build & Configuration Instructions
The project uses modern `pyproject.toml` packaging (via `hatchling`).

### Environment Variables
For agent creation and AI-powered tasks, the following environment variables are available:
* **AI APIs:** `GEMINI_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`
* **Xovis Hub:** `XOVIS_HUB_CLIENT_ID`, `XOVIS_HUB_CLIENT_SECRET`

**Local Environment Setup:**
```bash
# Create venv and install the package in editable mode with all dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"

```

**Required Runtime Infrastructure:**

* **uvloop:** Automatically utilized if available on the host OS to maximize standard `asyncio` performance.
* **Redis (Downstream Bridge):** Certain downstream integrations require Redis (`redis://localhost:6379/0`) for high-speed data offloading.

## Enterprise Testing Standards (SDET Rules)

We use `pytest`, `pytest-asyncio`, and `respx` (for HTTP mocking). Testing is strictly organized into four execution tiers:

1. **Tier 1 (Smoke & Stateless):** Validates baseline connectivity, API routing, utility normalization (e.g., `XovisTime` unit tests), and read-only operations.
2. **Tier 2 (Stateful Configuration):** Validates Desired State Configuration (DSC) and CRUD operations (e.g., Geometries, Logics, DataPush).
3. **Tier 3 (The Data Plane):** Validates high-frequency telemetry pipelines, socket stream parsing, and standard `XovisSink` protocol compliance.
4. **Tier 4 (Endurance/Integrity):** Cross-references telemetry streams against the historical `sensor_db` to guarantee pipeline alignment. **Rule:** These tests require a minimum 75-second aggregation window wait to ensure hardware bin closure, followed by a retry loop (up to 60s) for firmware DB commit latency.

**Immutable Testing Rules:**

1. **Strict Idempotency (CRITICAL):** All E2E hardware tests (Tier 2/3/4) MUST be fully idempotent. Mutating tests are tagged with `@pytest.mark.destructive`. Resource creation and deletion MUST be wrapped in a `try...finally` block to guarantee hard teardown.
2. **Teardown Order (CRITICAL):** When cleaning up DataPush resources, you MUST delete all `DataPushAgent` instances BEFORE deleting the `DataPushConnection`. Attempting to delete a connection with active agents will trigger an HTTP 400 "Connection in use" error.
3. **Consolidated CRUD Testing:** Redundant configuration tests (e.g., `test_datapush.py`) MUST be consolidated into the robust Tier 2 suite (`test_cp_datapush_crud.py`) to minimize hardware mutation overhead while maintaining full coverage.
4. **Pacing and Resource Limits:** E2E tests for resource provisioning (Connections/Agents) must respect the SDK's `_pacing_delay()`. Use `id_mode="SERVER"` to let the hardware manage resource indexing.
5. **Clock-Aware Assertions:** When validating historical data (Tier 4), queries MUST use the sensor's internal clock (via `get_state`) to construct ISO8601 windows, neutralizing runner-to-sensor drift.
6. **Proactive Capability Skips:** Destructive E2E tests must be protected at the top of the function with awaited proactive hardware checks (e.g., `if not await real_device.has_analytics: pytest.skip(...)`).
7. **Fixture Scopes (CRITICAL):**
   * **Hub Tests:** MUST use `@pytest_asyncio.fixture(scope="session")` for the `HubClient` to prevent Auth0 HTTP 429 rate-limit blocks.
   * **Local Device Tests:** MUST use `@pytest_asyncio.fixture(scope="function")` for `DeviceClient`. `httpx` aggressively binds its connection pool to the active event loop; sharing a client across tests will cause `RuntimeError: Event loop is closed`. Yield the client and aggressively `await client.aclose()`.
8. **No Dummy Data:** Never use fake MAC addresses for Hub tests. Dynamically fetch a valid device ID via `get_devices()` before attempting updates.
9. **Parametrized Matrices:** Stream and DataPush validation utilizes exhaustive `@pytest.mark.parametrize` matrices combining agent types, targets (Single vs. Multi), transport protocols (TCP, HTTP, UDP), and retry schemas.