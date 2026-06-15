# Quadrifurcated Architecture

The `xovis-sdk` is strictly **quadrifurcated** into four distinct planes. This decoupling ensures high-frequency telemetry remains unblocked by slow control operations, while fleet-wide state is managed independently of the hardware's physical lens topology.


!!! info "Xovis HUB Pro"
    Operating the SDK on the Cloud HUB free tier may result in rate limit exhaustion during bulk operations. A **Xovis HUB Pro** subscription is suggested for production environments.

### System Data Flow

```mermaid
graph TB
    subgraph "Xovis Hardware Layer"
        direction TB
        A[Physical Sensors / Spiders]
        H[Xovis HUB Cloud]
        H -- Secure Proxy Tunnel (M2M) --> A
    end

    subgraph "Data Plane (High Frequency)"
        B[XovisTCPServer / XovisUDPServer / XovisHTTPServer]
        S[XovisSink]
    end

    subgraph "Control & State Plane (SDK Core)"
        C[DeviceClient]
        F[HubClient]
        D[HostStateBucket / ConfigCache]
        
        F -- "connect_device()" --> C
        C <--> D
    end

    subgraph "Agentic & Tooling Layer"
        G[XovisAIToolkit]
        M[MCP Server / Model Context Protocol]
        R[REPLAccessor / CLI]
    end

    %% Data Connections
    A -->|Live-Push up to 12.5Hz| B
    B -->|Sliding Buffer Extraction| S

    %% Control Connections
    A <-->|Local REST API v5| C
    H <-->|Hub REST API| F
    
    %% Fleet Integration
    D -. "Reflect State" .-> R
    F -. "Fleet Sync" .-> D

    %% AI Integration
    D --- G
    F --- G
    G --- M
    M --- LLM[LLM / Autonomous Agents]

    %% Styling
    style A fill:#1e293b,stroke:#38bdf8,stroke-width:2px
    style H fill:#1e293b,stroke:#38bdf8,stroke-width:2px
    style B fill:#0f172a,stroke:#2dd4bf,stroke-width:2px
    style C fill:#0f172a,stroke:#2dd4bf,stroke-width:2px
    style F fill:#0f172a,stroke:#2dd4bf,stroke-width:2px
    style G fill:#1e293b,stroke:#818cf8,stroke-width:2px
    style M fill:#1e293b,stroke:#818cf8,stroke-width:2px
```

---


!!! info "For Contributors"
    If you are interested in collaborating on the SDK or want to understand the technical rules governing each plane, please refer to the [Contributor Architecture & Guidelines](contributing/agent_instructions.md).

### 1. The Data Plane (Telemetry Ingestion)
**Module:** `src/xovis/datapush/`

The engine designed for high-frequency Live-Push (up to 12.5Hz) ingestion of live tracking telemetry from physical sensors.

- **Objective**: Zero-copy, maximum throughput, non-blocking ingestion.
- **Engine**: Pure native `asyncio` enhanced by `orjson` for high-performance JSON deserialization.
- **DataPush Variety**: Supports multiple transmission types:
    - **Live-Push**: High-speed coordinate data at up to **12.5Hz**.
    - **Logic-Push**: Minutely state transitions and counts.
    - **Status & Recording**: Diagnostic health and configuration-based data offloading.
- **Protocol Fidelity**: Unified ingestion strategy across HTTP, UDP, TCP, and MQTT.
    - **Data Handling**: Optimized to handle raw, concatenated JSON data (TCP) via a **Sliding String Buffer** and `json.JSONDecoder().raw_decode()`.
    - **Packet Handling**: Uses `orjson` for discrete packet ingestion (HTTP, UDP, MQTT) to minimize CPU overhead.
- **Key Features**:
    - **High Throughput**: Telemetry is instantly offloaded to `XovisSink` protocols.
    - **Binary Fallback**: Automatically wraps non-JSON payloads (e.g., binary recordings) into a standardized `recording_data` frame.
    - **Connection Filtering**: Centralized logic to intercept and ignore sensor heartbeat/connection tests before they reach sinks.

```mermaid
graph TD
    subgraph "Xovis Hardware / Event Stream"
        Sensor["Physical Sensor"]
    end

    subgraph "Data Plane (Ingestion Pipeline)"
        subgraph "Ingestion Servers (asyncio / zero-blocking)"
            TCP[XovisTCPServer]
            UDP[XovisUDPServer]
            HTTP[XovisHTTPServer]
            MQTT[AnyMQTTServer]
        end

        subgraph "Stream Processing"
            Heartbeat{"Heartbeat / Test?"}
            Sliding["Sliding String Buffer"]
            RawDecode["json.raw_decode"]
            Orjson["orjson.loads"]
            BinaryWrap["Binary Fallback / Wrap"]
        end
    end

    subgraph "Downstream"
        Sink["XovisSink Protocol"]
    end

    Sensor -->|Raw Telemetry Stream| TCP
    Sensor -->|UDP Packets| UDP
    Sensor -->|HTTP Webhook| HTTP
    Sensor -->|MQTT Messages| MQTT

    TCP -->|Raw Concatenated JSON| Sliding
    Sliding --> RawDecode
    UDP --> Orjson
    HTTP --> Orjson
    MQTT --> Orjson

    RawDecode --> Heartbeat
    Orjson --> Heartbeat

    Heartbeat -->|Yes| Drop["Ignore / Filter Out"]
    Heartbeat -->|"No (Valid Payload)"| Sink
    
    Sensor -->|Non-JSON payload - Recording| BinaryWrap
    BinaryWrap --> Sink
```

### 2. The Control Plane (Configuration Management)
**Module:** `src/xovis/api/`

Low-frequency REST API wrappers for configuring the Xovis HUB Cloud and physical Edge sensors.

- **Objective**: Robustness, strict schema adherence, and resilience.
- **Engine**: `httpx` for networking and `Pydantic V2` for comprehensive model validation.
- **Safety**: Integrates with the `XovisSafetyGuardrail` to ensure operational security.
- **Key Features**:
    - **Proactive Probing**: Caches hardware capabilities to optimize performance and reliability.
    - **XovisTime Utility**: Standardizes all time-sensitive inputs into UTC Unix milliseconds.
    - **Cloud Tunneling**: Provides secure access to edge devices through the Cloud HUB proxy.

```mermaid
graph TD
    subgraph "Application Layer"
        DevCode[Developer / SDK Scripts]
    end

    subgraph "Control Plane Core"
        subgraph "Clients"
            HC[HubClient]
            DC[DeviceClient]
            Smart[SmartDeviceClient]
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

### 3. The State & Topology Plane (Fleet Orchestration)
**Module:** `src/xovis/api/device/`

A stateful, topology-aware engine that abstracts complex sensor graphs into human-readable mappings.

- **Objective**: Transparent management of multisensor environments and offline-first state persistence. The [Xovis Mission Control TUI](cli.md#ui) serves as the primary visual interface for configuring these buckets and detecting hardware topologies.
- **Engine**: `TopologyManager` + `ConfigCacheManager`.
- **Logic**:
    - **Context Isolation**: Distinguishes between physical lenses (`singlesensor`) and virtual stitched environments (`multisensors`).
    - **Offline Persistence**: Enables zero-latency lookups via localized state caching.
    - **Dynamic Discovery**: Automatically identifies hardware topologies and registers them for easy access.

#### Interaction: Topology and StateBucket

The `TopologyManager` and `StateBucket` work together as the "map" and the "content" of your Xovis system. While the `TopologyManager` defines how physical hardware and virtual environments are structured, the `StateBucket` stores the actual serialized configuration data for each part of that structure.

##### The Core Workflow

1. **Topology Discovery:** The `client.topology` manager identifies which contexts exist. It discovers if the sensor is a standalone device (`singlesensor`) or part of a stitched `multisensor` cluster.  
2. **Cache Synchronization:** When you call `await client.cache.sync()`, the SDK queries the topology map to find all active physical and virtual context endpoints.  
3. **StateBucket Storage:** For every context identified in the topology, the SDK populates a localized `StateBucket` containing the specific zones, lines, and agents belonging to that context.

```mermaid
graph TD
    subgraph DeviceClient [Device Client Instance]
        T["<b>Topology Manager</b><br/><i>The Map</i>"]
        C["<b>Config Cache Manager</b><br/><i>The Orchestrator</i>"]
    end

    subgraph Network [LAN & Remote Network]
        L[Physical Lens]
        MS[Multisensor Cluster]
    end

    T -- "Scans & Discovers" --> Network
    C <-- "Uses Map from" --> T

    subgraph Buckets [State Buckets / Contexts]
        SB1["<b>Bucket: singlesensor</b><br/>Zones, Lines, Agents"]
        SB2["<b>Bucket: multisensor_1</b><br/>Multisensor Zones, Logics"]
    end

    C -- "Populates & Manages" --> Buckets

    SB1 -- "Represents Data for" --> L
    SB2 -- "Represents Data for" --> MS
```
When you execute `client.cache.export_to_file("device_state.json")`, the SDK aggregates all localized `StateBuckets` structured by the `TopologyManager` and dumps them into a single, cohesive offline state JSON file.

### 4. The Agentic Layer (AI Orchestration)
**Module:** `src/xovis/skills/`

The integration layer for autonomous agents, LLMs, and the Model Context Protocol (MCP).

- **Objective**: Bridging hardware operations with natural language reasoning while maintaining enterprise safety.
- **Engine**: `XovisAIToolkit` + `AIPrivacySession`.
- **Safety Tiering**:
    - **Privacy Pseudonymization**: Protects sensitive identifiers before they reach external models.
    - **Tool Mapping**: Categorizes every operation into clear safety levels (OPEN, RESTRICTED, CRITICAL, BLOCKED).
    - **MCP Integration**: Exposes the SDK as a standardized toolset for AI-enabled environments.

```mermaid
graph TD
    subgraph "External AI Space"
        LLM[LLM / Autonomous Agents]
    end

    subgraph "Agentic Layer (Safety & Privacy)"
        subgraph "Model Context Protocol"
            MCP[MCP Server]
        end

        subgraph "AI Privacy Boundary"
            Priv[AIPrivacySession]
            Hash[Pseudonymization / Hashing]
            Deanonymize[Post-Process Deanonymizer]
        end

        subgraph "Safety Guardrails"
            TK[XovisAIToolkit]
            Guard[XovisSafetyGuardrail]
            Tools{Safety Tier Validation}
        end
    end

    subgraph "SDK Core / Hardware"
        SDK[SDK Operations / Client Calls]
    end

    LLM <-->|Natural Language / Tool Calls| MCP
    MCP <-->|Filter Sensitive Data| Priv
    Priv -->|MAC & Name Hashing| Hash
    Hash -->|Anonymized Input| LLM
    
    MCP -->|Requested Actions| TK
    TK --> Guard
    Guard --> Tools
    
    Tools -->|BLOCKED| Fail[Reject & Exception]
    Tools -->|CRITICAL| Human[Human-in-the-Loop Prompt]
    Tools -->|RESTRICTED| Warn[Warning & Pacing Delay]
    Tools -->|OPEN| Execute[Execute Directly]
    
    Execute --> SDK
    Human -->|Approved| SDK
    Warn --> SDK
    
    SDK -->|Plaintext Results| Deanonymize
    Deanonymize -->|Restore Real MACs/Names| Priv
```

---