# Contributor Architecture & Guidelines

This document provides a technical roadmap for developers and autonomous agents contributing to the `xovis-sdk`. It defines the architectural boundaries, technical principles, and safety guardrails required to maintain the SDK's enterprise-grade integrity.

## Contribution Principles

To maintain the high-performance and reliable nature of the SDK, every contribution must adhere to these four architectural planes. **Never mix the design patterns of these planes.**

### 1. The Data Plane (High-Frequency Telemetry)
**Path:** `src/xovis/datapush/`

The hot path for ingestion of Live-Push tracking telemetry (up to 12.5Hz). Contributions here prioritize throughput and non-blocking execution.

- **Objective**: Zero-blocking ingestion and high-speed data offloading.
- **Principle - Absolute Throughput**: Use native `asyncio` and `orjson` for lock-free deserialization.
- **Principle - Zero-Copy Handling**: Strictly no Pydantic validation in this path to prevent CPU saturation.
- **Technical Detail - Unified Ingestor**: Use the `DataPlaneIngestor` utility (in `utils.py`) for parsing and routing. It handles:
    - **TCP Data Handling**: `raw_decode` for concatenated TCP data.
    - **Packet Handling**: Fast `orjson` parsing for HTTP, UDP, and MQTT.
    - **Binary Fallback**: Automatic wrapping of non-JSON data into `recording_data` frames.

### 2. The Control Plane (Configuration Management)
**Path:** `src/xovis/api/`

REST API wrappers for configuring the Xovis HUB Cloud and local edge sensors. Contributions here prioritize schema adherence and resilience.

- **Objective**: Structural robustness and network resilience.
- **Principle - Strict Pydantic CRUD**: Every payload MUST be validated against auto-generated Pydantic V2 models.
- **Principle - Proactive Capability Checks**: Do not use `try...except` for missing hardware features. Use the lazy `_probe_capability` cache.
- **Principle - Normalized Time**: All time inputs MUST be processed via the `XovisTime` utility.

### 3. The State & Topology Plane (Fleet Orchestration)
**Path:** `src/xovis/api/device/` and `src/xovis/api/hub/`

A stateful engine that abstracts complex sensor graphs. Contributions here maintain the fleet-wide "Source of Truth."

- **Principle - Context Isolation**: Maintain the strict separation between `singlesensor` (physical) and `multisensors` (virtual) contexts.
- **Principle - Threaded Persistence**: Disk I/O for state caching MUST be offloaded using `asyncio.to_thread`.
- **Principle - Smart Topology**: The `TopologyManager` is responsible for synthesizing directed graphs (`StitchGraph`) from physical network nodes.

### 4. The Agentic Layer (AI Integration)
**Path:** `src/xovis/skills/`

The safety-first integration layer for autonomous agents and MCP.

- **Principle - Deterministic Resolution**: Use `uv` for all dependency management. Always respect the `uv.lock` file to ensure consistent cross-platform behavior.
- **Principle - Safety-by-Design**: Tools MUST be mapped to a `SafetyLevel`. Destructive operations require Human-in-the-Loop (HITL).
- **Principle - Zero-Trust Privacy**: The `AIPrivacySession` is the absolute boundary. Real identifiers (MACs, names) MUST NEVER reach the LLM.
- **Principle - Post-Execution De-anonymization**: Use `toolkit.privacy_session.deanonymize_text()` only when generating final reports for humans.

---

## Contributor Standards

### Coding Style

- **Zero-Inline-Comment, Max-Docstring**: Code must be self-explanatory. Use rigorous Google-style docstrings for architectural intent.
- **Pacing & Limits**: Always respect `_pacing_delay()` in E2E tests and production loops to prevent hardware saturation.

### Testing Requirements
The SDK uses a four-tier testing strategy. All PRs must include relevant tests:

1. **Tier 1**: Smoke tests for baseline connectivity.
2. **Tier 2**: CRUD validation (DSC/Idempotency).
3. **Tier 4**: Long-term stability and data alignment.

For implementation details, refer to the [Engineering Guidelines](engineering_guidelines.md).

