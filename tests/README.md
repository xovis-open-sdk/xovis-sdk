# Xovis SDK - Enterprise Testing Matrix

This directory contains the automated Software Development Engineer in Test (SDET) suite for the `xovis-sdk`. It is designed to run against live production hardware and the Xovis HUB Cloud. 

Because testing against physical edge devices introduces network latency, hardware capability constraints, state mutation, and event-loop complexities, this suite is architected around strict idempotency, proactive probing, and tiered execution.

## Execution Tiers

The test suite is built progressively. CI/CD pipelines must execute these tiers in order; if a lower tier fails, subsequent tiers are immediately aborted.

### Tier 1: Smoke & Stateless (`tests/api/`)
**Objective:** Validate baseline connectivity, API routing, and read-only operations.
* **Scope:** System info, Network configs, Time settings, Privacy modes, Users, ITxPT, Firmware Status, Hub device discovery, and capability probing (`has_wifi`, `has_analytics`).
* **Impact:** Safe to run continuously. No persistent state mutations.

### Tier 2: Stateful Configuration (`tests/api/device/`)
**Objective:** Validate Desired State Configuration (DSC) and CRUD operations.
* **Scope:** Creation and modification of Zones, Lines, Logics, Counters, DataPush Agents/Connections, Users, History retrieval, and Firmware Uploads.
* **Impact:** Marked with `@pytest.mark.destructive`. Requires strict idempotency protocols and proactive capability checks to prevent execution on unsupported hardware (e.g., lensless Spider NUCs).
* **Key Files:** `test_scene.py`, `test_analytics.py`, `test_datapush.py`, `test_users.py`, `test_itxpt.py`, `test_datapush_agents_matrix.py`, `test_datapush_connections_matrix.py`, `test_history.py`, `test_update.py`.

### Tier 3: The Data Plane (`tests/streams/`)
**Objective:** Validate high-frequency telemetry pipelines and backpressure handling.
* **Scope:** `XovisTCPServer`, `XovisHTTPServer` (Webhooks), `XovisUDPServer` (Datagrams), and asynchronous data delivery via the `XovisSink` protocol.
* **Impact:** High network utilization. Requires isolated asynchronous event loops and exhaustive parameterized matrices combining protocols, schedulers, and retry schemas.
* **Key Files:** `test_stream_tcp_raw.py`, `test_stream_udp_raw.py`, `test_stream_http_webhook.py`, `test_stream_matrix_exhaustive.py`.

### Tier 4: Endurance & Data Integrity
**Objective:** Cross-reference telemetry streams to guarantee firmware and pipeline alignment over extended durations.
* **Scope:** Validates that the 12.5Hz `LIVE_DATA` stream exactly matches the 1-minute `LOGICS` push and the physical sensor's historical database (`sensor_db`).
* **Key Files:** `test_data_alignment.py`.

---

## SDET Architecture Rules

### 1. Fixture Scoping (`conftest.py`)
* **HubClient (`scope="session"`):** The Xovis HUB Cloud is protected by Auth0. The `real_hub` fixture is session-scoped to fetch a single token and prevent HTTP 429 Rate Limit exhaustion during the test run.
* **DeviceClient (`scope="function"`):** `httpx` binds connection pools to the active event loop. The `real_device` fixture is function-scoped. It yields a fresh client and aggressively executes `await client.aclose()` to prevent `RuntimeError: Event loop is closed` across concurrent tests.

### 2. Proactive Capability Probing
Tests must not blindly execute and rely on HTTP 403/404 errors to determine hardware capabilities. Destructive tests MUST evaluate the asynchronous `_probe_capability` cache before execution to gracefully skip unsupported hardware.

### 3. Strict Idempotency & Topology
Any test that modifies the sensor state MUST guarantee cleanup, even if an assertion fails midway. This prevents the physical device from running out of memory slots for geometries or logics. Tests must strictly operate within the context-aware topology (e.g., `real_device.singlesensor`).

**Required Pattern (Single Entity):**
```python
@pytest.mark.asyncio
@pytest.mark.destructive
async def test_resource_crud(real_device: DeviceClient) -> None:
    """
    Validates the complete lifecycle of a Scene Geometry.
    Guarantees physical hardware teardown via strict finally blocks.
    """
    if not await real_device.has_analytics:
        pytest.skip("Analytics capability not supported on this hardware.")

    created = await real_device.singlesensor.scene.create_geometry(payload)
    try:
        assert created.id is not None
    finally:
        await real_device.singlesensor.scene.delete_geometry(created.id)

```

**Required Pattern (Nested Dependencies):**
For resources that depend on each other (e.g., an Agent assigned to a Connection), you must use nested `try...finally` blocks to ensure both entities are deleted even if one deletion fails or an assertion crashes.

```python
@pytest.mark.asyncio
@pytest.mark.destructive
async def test_agent_connection_dependency(real_device: DeviceClient) -> None:
    """
    Validates interdependent DataPush entity creation and cascading teardown.
    """
    conn = await real_device.singlesensor.datapush.create_connection(conn_payload)
    try:
        agent = await real_device.singlesensor.datapush.create_agent(agent_payload)
        try:
            assert agent.connection_id == conn.root.id
        finally:
            await real_device.singlesensor.datapush.delete_agent(agent.id)
    finally:
        await real_device.singlesensor.datapush.delete_connection(conn.root.id)

```

---

## Running the Tests

Ensure your `.env` file or GitHub Actions Secrets are populated with both sensor and HUB credentials (`XOVIS_TEST_HOST`, `XOVIS_TEST_USER`, `XOVIS_HUB_CLIENT_ID`, etc.).

**Run All Tests (Local / Single User):**

```bash
pytest tests/

```

**Run Only Non-Destructive Smoke Tests (CI/CD Pipeline Guardrail):**
Because concurrent PRs running destructive tests against a single live physical sensor will cause race conditions and corrupt the hardware configuration, automated PR triggers MUST strictly isolate test execution.

```bash
pytest tests/ -m "not destructive"

```