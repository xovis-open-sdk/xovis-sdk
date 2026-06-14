# Xovis SDK

Welcome to the **xovis-sdk** documentation. This is an enterprise-grade, high-performance Python SDK designed to intercept, parse, and normalize data from Xovis 3D stereo-vision sensors and orchestrate fleets via the Xovis HUB Cloud.

Compliance Note: This project is an independent, open-source initiative. It is not officially affiliated with, maintained by, or endorsed by Xovis AG.

[![GitHub](https://img.shields.io/badge/GitHub-xovis--sdk-181717?logo=github)](https://github.com/xovis-open-sdk/xovis-sdk)
[![PyPI](https://img.shields.io/pypi/v/xovis-sdk?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/xovis-sdk/1.0.0a3/)
[![MCP Ready](https://img.shields.io/badge/MCP-Ready-5B32A8.svg?logo=server&logoColor=white)](https://modelcontextprotocol.io/)
[![LangGraph Ready](https://img.shields.io/badge/LangGraph-Ready-1C3C3C.svg?logo=langchain&logoColor=white)](https://langchain.com/)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI-Compatible-412991.svg?logo=openai&logoColor=white)](https://openai.com/)
[![Anthropic Compatible](https://img.shields.io/badge/Anthropic-Compatible-D2B8A3.svg?logo=anthropic&logoColor=black)](https://www.anthropic.com/)
[![CrewAI Ready](https://img.shields.io/badge/CrewAI-Ready-FF4B4B.svg?logo=google-cloud&logoColor=white)](https://crewai.com/)
[![Cursor Optimized](https://img.shields.io/badge/Cursor-Optimized-000000.svg?logo=python&logoColor=white)](https://cursor.sh/)

## Key Features

- **Quadrifurcated Architecture**: Separation of Data, Control, State, and Agentic planes.
- **Zero-Copy Telemetry**: 12.5Hz ingestion with binary packing.
- **Fleet Orchestration**: Resilient bulk operations via Xovis HUB Cloud.
- **Topology Awareness**: Automatic resolution of physical vs. virtual sensor contexts.
- **AI-Ready**: Native toolkits for OpenAI, Anthropic, LangGraph, and Model Context Protocol (MCP) support.

## AI & Autonomous Agents

The Xovis SDK is built for the agentic era. It transforms hardware into "Live Resource Providers" for AI:

- **Universal Tool Adapter**: Projects SDK methods as strictly validated tools for GPT-5.5 and latest Anthropic models.
- **MCP Server**: Native integration for Cursor, Windsurf, and Claude Desktop.
- **Safety Guardrails**: Human-in-the-loop confirmation for high-impact operations and 350-device safety thresholds for fleet operations.
- **Documentation Excellence**: >75% docstring coverage with strict Google-style enforcement.

Explore the [AI & Agents](ai/agentic_layer.md) section for more.

## Installation & Setup

The Xovis SDK is modular. Choose the installation that fits your deployment:

### 1. Standard Installation
Core SDK for local sensor interaction and cloud orchestration.
```bash
pip install xovis-sdk
```

### 2. High-Performance (Recommended for Linux/macOS)
Includes `uvloop` for maximum socket throughput in the Data Plane. On Windows, the SDK automatically utilizes the high-performance `ProactorEventLoopPolicy`.
```bash
pip install "xovis-sdk[uvloop]"
```

### 3. Full Mission Control (TUI & AI)
Includes the terminal interface (TUI) and AI Agentic Layer dependencies.
```bash
pip install "xovis-sdk[tui,ai]"
```

## Quick Start: CLI Mission Control

Launch your environment in seconds using the built-in CLI.

1. **Warmup**: Synchronize schemas from your sensor.
   ```bash
   xovis-cli warmup <SENSOR_IP>
   ```
2. **Type Generation**: Create strict Python types for your IDE.
   ```bash
   xovis-cli generate-types
   ```
3. **Launch Terminal**: Open the interactive dashboard.
   ```bash
   xovis-cli ui
   ```

For advanced orchestration and fleet-wide commands, see the [CLI Reference](cli.md).

## Next Steps

Dive straight into the [API Reference](api/index.md) for more.
