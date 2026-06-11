# xovis-sdk - Architecture & Engineering Guidelines

This document defines the architectural principles, boundaries, and hard-learned technical rules for the `xovis-sdk`. It acts as the definitive Universal Translator for Xovis hardware, cleanly decoupling raw edge data from downstream enterprise software.

## Core Philosophy: The Quadrifurcated Architecture

To handle 12.5Hz DataPushes without destabilizing, while simultaneously orchestrating complex multisensor graph topologies and cloud fleets, we cannot rely on a single monolithic framework. Standard synchronous libraries block the event loop, and Pydantic introduces crippling serialization overhead if used in high-frequency ingestion loops.

Therefore, the `xovis-sdk` architecture is strictly quadrifurcated into four distinct operational planes. **Never mix the design patterns of these planes.**

---

### 1. The Data Plane (High-Frequency Telemetry Ingestion)

**Path:** `src/xovis/streams/`
For raw TCP, HTTP Webhook, and UDP DataPush streams (e.g., `LIVE_DATA` running an `IMMEDIATE` scheduler), the objective is zero-copy, non-blocking maximum throughput.

* **Core Engine:** We use pure native asyncio (`asyncio.start_server`, `asyncio.DatagramProtocol`) enhanced by `uvloop` (where available on Linux/macOS) or `WindowsProactorEventLoopPolicy` to manage raw sockets and datagrams via `XovisTCPServer`, `XovisHTTPServer`, and `XovisUDPServer`.
* **Parsing Strategy:** Xovis streams raw concatenated JSON objects without newlines or length prefixes. You MUST maintain a sliding string buffer combined with the standard library's `json.JSONDecoder().raw_decode()`. This safely slices frames out of the continuous stream without crashing on incomplete fragments. Do NOT use `orjson` for this specific extraction step.
* **Data Packing:** STRICTLY NO Pydantic validation is allowed in this hot path. High-performance data structures and optimized serialization are used to prepare payloads for downstream sinks.
* **Network I/O:** Telemetry frames are delivered to attached sinks in real-time. Lock-free archiving and efficient batching are strictly enforced to prevent data loss or ingestion delays.

---

### 2. The Control Plane (Low-Frequency REST API)

**Path:** `src/xovis/api/`
For configuring the Xovis HUB Cloud and local sensors, the priority flips from raw speed to structural robustness, strict schema adherence, strict authentication rules, and network resilience.

* **Networking:** We use `httpx` for asynchronous HTTP connection pooling, strict redirect handling (essential for navigating Hub domain migrations from `.com` to `.cloud`), and supporting NTLM authentication for local sensor Windows SSO.
* **Token Resilience:** Auth0 aggressively rate-limits token requests. The SDK implements an authoritative `HubAuth` manager that handles stateful token caching (saving valid JWTs to disk and memory for 24 hours) and utilizes an `asyncio.Lock()` to autonomously intercept and refresh tokens.
* **Error State Resolution:** Code must gracefully differentiate operational failures. `HTTP 401 Unauthorized` triggers an automatic token refresh. `HTTP 403 Forbidden` indicates a strict privilege constraint (user role lacks permission) or a hardware-level tenant boundary; this must be gracefully surfaced to the user or agent, not brute-forced. `HTTP 404 Not Found` indicates a privacy mode mismatch or unavailable endpoint.
* **Proactive Hardware Probing:** Do not rely on brittle `try...except 403/404` blocks for missing hardware features. The SDK utilizes a lazy, asynchronous `_probe_capability` cache (e.g., `client.has_wifi`, `client.has_analytics`, `client.has_itxpt`) to proactively handle hardware constraints.
* **Time Normalization (XovisTime):** The SDK implements a unified time parser (`src/xovis/utils/time.py`) that normalizes all time-sensitive inputs. It supports relative strings (e.g., `"-1h"`, `"now"`), ISO 8601 strings (including timezone offsets like `"+02:00"`), and native `datetime` objects. All inputs are converted to UTC Unix milliseconds to ensure consistent hardware querying regardless of the sensor's local timezone configuration.
* **Data Validation:** We employ Pydantic v2 heavily here. The massive OpenAPI YAMLs are generated into strict `RootModels` using alias mapping.
* **DataPush Configuration Nuances:** In `DataPushConnection` configurations (specifically `HTTPConfig`), the `uri` must exclude the port (e.g., `http://10.0.0.1/webhook`), which must be provided in the separate `port` field. For `TCPConfig` and `UDPConfig`, the `uri` must include the protocol prefix (e.g., `tcp://10.0.0.1` or `udp://10.0.0.1`) to satisfy strict validation. Furthermore, `DataPushAgent` instances MUST have `enabled=True` explicitly set; otherwise, Pydantic's `exclude_unset=True` will strip the field, leaving the agent deactivated on the sensor.
* **DataPush Trigger Boundaries:** DataPush agents for `STATUS` and `VALIDATION_RECORDING` do NOT support manual retriggering via the `/trigger` endpoint. Logic must skip trigger calls for these types.
* **The Bridge Layer:** Implements a version-agnostic manual bridge layer (`src/xovis/models/device.py`) that abstracts firmware-specific JSON variations into stable SDK properties. Supports complex Custom Logic (RPN filters, age histograms), spatial entities (Lines, Masks, Blocked Spaces), core business logic (Logics, Layers, ObjectTypes), and high-frequency DataPush pipelines (Agents, Connections, manual triggers).
* **Pushing Configurations:** When pushing configs back to the device or hub, you MUST strictly enforce `.model_dump(mode="json", exclude_unset=True)` to ensure enumerations and `AnyUrl` objects serialize cleanly over the wire to prevent HTTP 400 rejections.

---

### 3. The State & Topology Plane (Fleet Engine)

**Path:** `src/xovis/api/device/` and `src/xovis/api/hub/`
The SDK goes beyond stateless HTTP requests by maintaining graph-aware context, stateful caching, and Desired State Configuration (DSC) workflows, empowering developers to orchestrate entire fleets natively.

* **Ecosystem Topology:** An IP address represents a **Host**. A host runs isolated **Contexts**. SDK namespacing MUST reflect this strict segregation (e.g., `device.singlesensor.datapush` vs `device.multisensors.by_name.Terminal_A.scene`).
* **Singlesensor (SS):** The context representing a physical edge device equipped with optical lenses. Responsible for raw localized telemetry and optical imagery.
* **Multisensor (MS):** The context representing a virtual, stitched tracking environment spanning 0..N physical sensors seamlessly combined into a unified trackable area.
* **Spider Nodes:** High-compute, lensless processing devices (SPI-PU1/PU2). Spiders *only* run Multisensor contexts and bridge telemetry. The SDK MUST gracefully intercept physical lens requests (e.g., fetching `/images/raw_left.jpg`) and raise a `HardwareNotSupportedError` when communicating with a Spider.
* **Stateful Caching (`ConfigCacheManager` & `HubCacheManager`):** Maintains RAM-cached configurations. The `ConfigCacheManager` enforces strict context-isolated persistence by rooting multisensor contexts into the `HostStateBucket` via a dedicated setter. This prevents "ghost" state updates where resources are added to temporary facades instead of the authoritative bucket.
* **String-Normalized ID Resolution:** All cache lookups and resource managers MUST use string normalization for IDs. This guarantees consistency between the SDK's internal dictionary keys and the hardware's variable JSON types (int/str).
* **The GC Trap:** If `BACKGROUND_WATCHER` is active, the `asyncio.create_task` polling loop MUST be stored in a hard-referenced `Set` (`_background_tasks.add()`). This prevents Python 3.11+ aggressive Garbage Collection from deleting the task mid-execution.
* **Lifecycle Teardown:** Background tasks must be cleanly cancelled during the client's `__aexit__` context closure to prevent memory leaks and "Event loop closed" crashes.
* **Offline-First Persistence:** The `ConfigCacheManager` supports auto-persistence via `auto_persist_path`. Disk serialization and deserialization of the `HostStateBucket` are safely offloaded using `asyncio.to_thread` to guarantee zero blocking of the async event loop during disk I/O.
* **Edge Topology Synthesis:** The `TopologyManager` synthesizes directed graphs (`StitchGraph`) by concurrently cross-referencing multisensor child clusters with physical local network nodes (mapping MACs to local IPs).
* **Firmware Autonomy:** Includes a passive `DiscoveryManager` that identifies unknown hardware API fields during synchronization.
* **Internal Agentic Loop:** Leverages an internal `SchemaAnalyst` skill (Gemini-powered) to perform semantic structural analysis on discovered firmware deltas, proposing bridge model updates to maintain "Universal Translator" status without breaking production stability.
* **The Dynamic Hub-to-Edge Bridge:** `HubClient.connect_device()` securely intercepts OAuth2 tokens to dynamically spawn `DeviceClient` instances routed through the Cloud HUB. The SDK absolutely MUST use the dynamic OpenAPI standard route: `f"{base_url}/devices/{mac_address}/tunnel"`. Hardcoded fallback proxy strings are strictly forbidden.
* **Fleet Bulk Execution:** Operations on Hub fleets or Multisensor stitched children utilize `bulk_execute`. This leverages `asyncio.gather(return_exceptions=True)` and strict context management to ensure that offline devices return isolated exceptions mapped within a `BulkResult[T]` object, preventing a single offline camera from crashing the orchestration pipeline.
* **Hub Tunnel Concurrency & Serialization:** Parallel operations targeting a specific device through the Hub tunnel (e.g., via LangChain tools) MUST be serialized using a per-device `asyncio.Lock` keyed by MAC address. This lock must wrap the *entire* connection lifecycle (`connect_device`) and any internal context aggregation loops to prevent Hub reverse proxy saturation (HTTP 503).
* **Tunnel Resilience & Connection Pooling:** Tunneled `DeviceClient` instances MUST enforce a 60-second timeout for heavy edge aggregations and use strict `httpx.Limits(max_connections=2, max_keepalive_connections=1)` to recycle sockets cleanly and prevent proxy exhaustion.

### 4. The Agentic Layer (Universal Tool Adapter)

**Path:** `src/xovis/skills/`
The "Universal Translator" for autonomous agents and LLMs, providing safe, pseudonymized, and strictly validated hardware orchestration.

* **Privacy First:** The `AIPrivacyEngine` handles two-way mapping of sensitive identifiers (MAC addresses, Customer names) to format-preserving hashes, ensuring zero-trust boundaries when interacting with external LLMs.
* **Safety Guardrails:** Every tool is assigned a `SafetyLevel` (OPEN, RESTRICTED, CRITICAL, BLOCKED). CRITICAL operations (e.g., factory reset) require explicit human-in-the-loop confirmation.
* **Strict Operational Constraints:** The toolkit uses a strictly defined mapping of SDK methods to tools. It does not automatically expose the entire underlying REST API or SDK.
* **Agentic Discovery:** Leverages the `SchemaAnalyst` (internal) to autonomously propose code-level updates to the bridge layer when new hardware features are detected in the wild.

---

### 5. Hyper-Optimized Developer Experience (DX)

We prioritize human-centric API design without sacrificing static type safety. Auto-completion and resource resolution are treated as core native features.

* **Smart Resolvers & Conflict Handling:** Configuration methods (e.g., `delete_geometry`) accept `id_or_name: Union[str, int]`. They use a fast-path for exact IDs (bypassing network lookups) and fall back to context-aware RAM cache lookups for human-readable string names. Conflicting names raise a `MultipleResourcesFoundError` explicitly detailing the MAC addresses and Customer context to aid immediate script correction.
* **Runtime Autocomplete (Jupyter/IPython):** Standard collections are wrapped in a `REPLAccessor` (`CacheCollection`). This exposes dynamic `.by_name.` and `.by_mac.` dot-notation tailored to the specific context. Interactive environments will generate instant, live autocomplete dropdowns (e.g., `device.multisensors.by_name.Terminal_A.scene.zones.by_name.[TAB]`).
* **Static Autocomplete (VS Code/PyCharm):** The SDK provides an offline `xovis.cli` sync script that crawls a serialized cache graph to generate a local `xovis_types.py` file. It partitions `Literal` strings (e.g., `SinglesensorZoneName = Literal[...]`) to prevent context-bleeding. The CLI features zero-dependency ANSI color outputs, generation analytics ("the receipt"), `--dry-run` safety, dynamic path resolution anchoring (`Path(__file__)`), and leverages native `subprocess.run(["ruff", "format", ...])` to ensure compliance.

---

### 6. The Open Core Boundary (Sink Protocol)

This architectural separation enforces the "Open Core" boundary. The open-source SDK acts as an incredibly fast universal translator, cleanly exposing the `XovisSink` Protocol (`src/xovis/streams/sinks.py`). External developer logic is injected via this protocol, passing processed telemetry data up to proprietary downstream engines (e.g., Kafka, Redis Streams) without bottlenecking the real-time VMS requirements.

---

### 7. Enterprise Coding & Documentation Standards

* **Zero-Inline-Comment, Max-Docstring:** The SDK enforces the "Clean Code" philosophy. Inline developer chatter (e.g., `# create the connection`) is strictly forbidden. The code must explain itself. Architectural intent, Pydantic constraints, and plane boundaries MUST be formalized into rigorous, maxed-out Google-style docstrings for every module, class, and method. (Exception: compiler/linter directives like `# type: ignore` are permitted).

---

### 8. Enterprise Testing Standards (SDET Rules)

**Path:** `tests/`
We use `pytest`, `pytest-asyncio`, and `respx` to test against live hardware. Testing is strictly organized into four execution tiers:

* **Tier 1 (Smoke & Stateless):** Validates baseline connectivity, API routing, utility normalization (e.g., `XovisTime` unit tests), and read-only operations.
* **Tier 2 (Stateful Configuration):** Validates Desired State Configuration (DSC) and CRUD operations (e.g., Geometries, Logics, DataPush).
* **Tier 3 (Data Plane):** Validates high-frequency telemetry pipelines, TCP/UDP/HTTP stream parsing, and standard `XovisSink` protocol compliance.
* **Tier 4 (Endurance/Integrity):** Cross-references telemetry streams against the historical `sensor_db` to guarantee pipeline alignment over extended durations.

**Immutable Testing Rules:**

* **Idempotency:** All E2E hardware tests (Tier 2/3/4) must be fully idempotent. Mutating tests are tagged with `@pytest.mark.destructive` and must perform a hard teardown inside a strict `finally` block to prevent hardware state exhaustion.
* **Teardown Sequence:** When cleaning up DataPush telemetry pipelines, agents MUST be deleted before their parent connections to avoid "resource busy" HTTP 400 errors.
* **Consolidated CRUD Testing:** Redundant configuration tests (e.g., `test_datapush.py`) MUST be consolidated into the robust Tier 2 suite (`test_cp_datapush_crud.py`) to minimize hardware mutation overhead while maintaining full coverage.
* **Proactive Capability Skips:** Destructive E2E tests must be protected at the top of the function with awaited proactive hardware checks (e.g., `if not await real_device.has_analytics: pytest.skip(...)`).
* **Hub Fixture Scopes:** Hub Tests MUST use `@pytest_asyncio.fixture(scope="session")` to share a single authenticated `HubClient`, preventing Auth0 HTTP 429 Rate Limit blocks.
* **Local Device Fixture Scopes:** Local Device Tests MUST use `@pytest_asyncio.fixture(scope="function")` for the `DeviceClient`. `httpx` aggressively binds its connection pool to the active event loop; sharing a local device client across tests will trigger catastrophic `RuntimeError: Event loop is closed` failures. The fixture must `yield` and forcefully `await client.aclose()`.
* **Parametrized Matrices:** Stream validation utilizes exhaustive `pytest.mark.parametrize` matrices combining agent types (LIVE_DATA, STATUS, LOGICS, WIFI_BT), targets (Single vs. Multi), transport protocols (TCP, HTTP, UDP), and specific retry schemas (BUFFER, DROP).
* **No Dummy Data:** Never use fake MAC addresses for Hub Integration tests. Dynamically fetch a valid device ID via `get_devices()` before attempting updates.
* **Strict Query Parameter Serialization:** All boolean flags in HTTP query parameters (e.g., `include_empty`, `force`, `volatile`) MUST be explicitly passed as lowercase strings `"true"` or `"false"`. Python's default capitalized `True`/`False` triggers `HTTP 500 Internal Server Error` in the sensor backend.
* **CacheCollection Iteration:** `CacheCollection` objects (e.g., `self.multisensors._contexts`) are natively iterable. Developers MUST cast them directly to a list (`list(self.multisensors._contexts)`) and NEVER call `.values()`, which will trigger an `AttributeError`.