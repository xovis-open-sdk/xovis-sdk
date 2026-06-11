# Xovis SDK - Implementation Examples

This directory contains a progressive sequence of examples designed to demonstrate the architectural layers of the `xovis-sdk`. 

The examples are structured as a logical learning path, moving from basic edge interactions up to high-frequency telemetry pipelines and enterprise-scale fleet orchestration.

---

**NOTICE: Xovis HUB Compatibility & Rate Limits**
This SDK is architected for enterprise-scale fleet orchestration. Due to the high concurrency of the `HubClient` and `bulk_execute` methods, a **Xovis HUB Pro** subscription is strongly suggested by the development team. Operating the SDK on the free tier may result in aggressive HTTP 429 Rate Limit exhaustion, which will disrupt automated provisioning and telemetry pipelines.

---

## Prerequisites

To execute these examples against live hardware or the Xovis HUB, you must define your environment variables. Copy the provided `.env.example` to `.env` in the root of the repository and populate it with your credentials:

```bash
# Edge Device Credentials
XOVIS_SENSOR_HOST="10.0.0.50"
XOVIS_SENSOR_PASS="your_password"

# Cloud HUB Credentials
XOVIS_HUB_CLIENT_ID="your_oauth_client_id"
XOVIS_HUB_CLIENT_SECRET="your_oauth_client_secret"

```

## The Learning Path

### [01_edge_basics.py](./01_edge_basics.py)

**Focus:** Control Plane, Proactive Probing, XovisTime & Offline-First State.
Demonstrates how to instantiate a `DeviceClient` with asynchronous offline-first disk persistence. Shows how to use proactive hardware checks (`is_spider`, `has_analytics`) to safely navigate capabilities, resolve objects by their human-readable names, and utilize the modernized `XovisTime` parser for flexible history queries (Relative, ISO 8601, and `datetime` support).

### [02_telemetry_pipeline.py](./02_telemetry_pipeline.py)

**Focus:** Data Plane, Protocol Parity & Lock-Free Ingestion.
Demonstrates how to deploy a high-frequency receiver pipeline across TCP, UDP, or HTTP Webhooks. It intercepts sensor streams and demonstrates the open-core plugin architecture by attaching multiple sinks (Diagnostic Logging and Redis zero-copy binary offloading).

### [03_topology_and_state.py](./03_topology_and_state.py)

**Focus:** Edge Topology Synthesis & DX CLI Tooling.
Demonstrates how to generate directed stitch graphs bridging MAC addresses to local IPs, navigate isolated virtual `multisensors` contexts, and export the device's state cache to JSON for the native `xovis-cli` IDE type generator.

### [04_fleet_orchestration.py](./04_fleet_orchestration.py)

**Focus:** Fleet Orchestration & Cloud Tunneling.
Demonstrates how to connect to the Xovis HUB, apply client-side filtering to target specific sites, and utilize `bulk_execute` to concurrently map configuration logic across hundreds of sensors using fault-isolated secure proxy tunnels.

## Execution

Ensure you are operating within your virtual environment with the SDK installed. Execute the scripts directly from the root directory to ensure relative paths load correctly:

```bash
python examples/01_edge_basics.py

```

