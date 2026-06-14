# Engineering Guidelines

This document defines the architectural principles, boundaries, and technical rules for the `xovis-sdk`. It serves as a deep-dive reference for engineers and agents building or extending the SDK's core capabilities.

## Core Philosophy: The Quadrifurcated Architecture

To handle 12.5Hz Live-Push DataPushes without destabilizing, while simultaneously orchestrating complex multisensor graph topologies and cloud fleets, the `xovis-sdk` architecture is strictly quadrifurcated into four distinct operational planes. **Never mix the design patterns of these planes.**

---

### 1. The Data Plane (High-Frequency Telemetry Ingestion)

**Path:** `src/xovis/datapush/`
The objective is zero-copy, non-blocking maximum throughput for raw TCP, HTTP Webhook, UDP, and MQTT DataPush streams.

* **Core Engine:** Pure native asyncio (`asyncio.start_server`, `asyncio.DatagramProtocol`) and `orjson` for lock-free deserialization.
* **Unified Ingestion:** Leverages the `DataPlaneIngestor` to standardize processing across all transport layers.
* **Parsing Strategy:** 
    - **TCP Streams**: Uses a sliding string buffer with `json.JSONDecoder().raw_decode()` to slice frames out of raw concatenated JSON streams.
    - **Discrete Packets**: Uses `orjson.loads()` for HTTP, UDP, and MQTT to minimize CPU overhead.
* **Binary Fallback**: Automatically wraps non-JSON payloads (e.g. recordings) in a `recording_data` pseudo-frame.
* **Data Packing:** STRICTLY NO Pydantic validation is allowed in this hot path.
* **Network I/O:** Telemetry frames are delivered to sinks in real-time. Efficient batching and lock-free archiving are enforced.

---

### 2. The Control Plane (Low-Frequency REST API)

**Path:** `src/xovis/api/`
Focuses on structural robustness, strict schema adherence, and network resilience for configuring hardware and cloud services.

* **Networking:** Uses `httpx` for asynchronous HTTP connection pooling and strict redirect handling.
* **Token Resilience:** The `HubAuth` manager handles stateful token caching and autonomous refreshes via `asyncio.Lock()`.
* **Proactive Hardware Probing:** Utilizes a lazy, asynchronous `_probe_capability` cache to prevent fragile 403/404 handling for missing hardware features.
* **Time Normalization (XovisTime):** Normalizes all time-sensitive inputs (relative strings, ISO 8601, datetime) to UTC Unix milliseconds.
* **Data Validation:** Employs Pydantic v2 heavily for structural validation of OpenAPI-generated models.
* **Configuration Nuances:** In `HTTPConfig`, the `uri` must exclude the port. `DataPushAgent` instances MUST have `enabled=True` explicitly set to prevent deactivation via `exclude_unset=True`.

---

### 3. The State & Topology Plane (Fleet Engine)

**Path:** `src/xovis/api/device/` and `src/xovis/api/hub/`
Maintains graph-aware context, stateful caching, and Desired State Configuration (DSC) workflows.

* **Ecosystem Topology:** Segregates between `Host` (IP), `Singlesensor` (physical lens), and `Multisensor` (virtual stitched environment).
* **Spider Nodes:** Intercepts physical lens requests for lensless Spider hardware and raises `HardwareNotSupportedError`.
* **Stateful Caching:** `ConfigCacheManager` enforces context-isolated persistence by rooting contexts into the `HostStateBucket`.
* **String-Normalized ID Resolution:** Guarantees consistency between SDK dictionary keys and hardware JSON types.
* **The GC Trap:** Background tasks MUST be stored in a hard-referenced `Set` to prevent Python 3.11+ Garbage Collection from deleting tasks mid-execution.
* **Offline-First Persistence:** Offloads disk I/O to threads via `asyncio.to_thread` to ensure zero blocking of the event loop.
* **The Dynamic Hub-to-Edge Bridge:** `HubClient.connect_device()` spawns `DeviceClient` instances routed through the Cloud HUB using standardized OpenAPI tunnel routes.
* **Hub Tunnel Concurrency:** Serializes parallel operations targeting a specific device through the Hub tunnel using a per-device `asyncio.Lock`.

---

### 4. The Agentic Layer (Universal Tool Adapter)

**Path:** `src/xovis/skills/`
Provides safe, pseudonymized, and strictly validated hardware orchestration for autonomous agents.

* **Privacy First:** `AIPrivacyEngine` handles two-way mapping of sensitive identifiers to format-preserving hashes.
* **Safety Guardrails:** Assigns a `SafetyLevel` (OPEN, RESTRICTED, CRITICAL, BLOCKED) to every tool.
* **Strict Mapping:** Only explicitly mapped SDK methods are exposed as tools to the AI.

---

### 5. Hyper-Optimized Developer Experience (DX)

* **Smart Resolvers:** Configuration methods accept IDs (fast-path) or names (cache fallback).
* **Runtime Autocomplete:** Uses `REPLAccessor` to expose dynamic `.by_name` and `.by_mac` dot-notation in interactive environments.
* **Static Autocomplete:** The `xovis-cli` generates local `xovis_types.py` files with partitioned `Literal` strings.

---

### 6. Enterprise Coding & Documentation Standards

* **Zero-Inline-Comment, Max-Docstring:** Architectural intent, Pydantic constraints, and plane boundaries MUST be formalized into rigorous Google-style docstrings.
* **Clean Code**: Code must explain itself; inline chatter is forbidden.

---

### 7. Enterprise Testing Standards (SDET Rules)

**Path:** `tests/`
Organized into four execution tiers (Smoke, Stateful, Data Plane, Endurance).

* **Idempotency:** All E2E hardware tests must be fully idempotent with hard teardowns in `finally` blocks.
* **Teardown Sequence:** Delete agents before parent connections.
* **Fixture Scopes:** Session-scoped `HubClient` to avoid 429s; function-scoped `DeviceClient` to prevent event loop closure errors.
* **Strict Parameter Serialization:** Boolean flags in query parameters MUST be passed as lowercase strings `"true"` or `"false"`.

---

### 8. Deterministic Dependency Management (uv)

The SDK uses `uv` for ultra-fast, deterministic dependency resolution and environment management.

* **Source of Truth**: The `pyproject.toml` defines the abstract requirements.
* **Locking**: The `uv.lock` file is the absolute, cross-platform source of truth for exact versions used in development and CI.
* **Resolution**: `uv` uses a high-performance SAT solver to prevent complex resolution loops.
* **Contributor Workflow**: 
    - Use `uv sync` to keep your environment aligned with the lockfile.
    - Always commit changes to `uv.lock` alongside `pyproject.toml` updates.