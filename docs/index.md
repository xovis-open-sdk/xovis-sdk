# Xovis SDK

Welcome to the **xovis-sdk** documentation. This is an enterprise-grade, high-performance Python SDK designed to intercept, parse, and normalize data from Xovis 3D stereo-vision sensors and orchestrate fleets via the Xovis HUB Cloud.

## 🚀 Key Features

- **Quadrifurcated Architecture**: Separation of Data, Control, State, and Agentic planes.
- **Zero-Copy Telemetry**: 12.5Hz ingestion with binary packing.
- **Fleet Orchestration**: Resilient bulk operations via Xovis HUB Cloud.
- **Topology Awareness**: Automatic resolution of physical vs. virtual sensor contexts.
- **AI-Ready**: Native toolkits for OpenAI, Anthropic, LangGraph, and Model Context Protocol (MCP) support.

## 🤖 AI & Autonomous Agents

The Xovis SDK is built for the agentic era. It transforms hardware into "Live Resource Providers" for AI:

- **Universal Tool Adapter**: Projects SDK methods as strictly validated tools for GPT-5.5 and latest Anthropic models.
- **MCP Server**: Native integration for Cursor, Windsurf, and Claude Desktop.
- **Safety Guardrails**: Human-in-the-loop confirmation for high-impact operations and 350-device safety thresholds for fleet operations.
- **Documentation Excellence**: >75% docstring coverage with strict Google-style enforcement.

Explore the [AI & Agents](ai/agentic_layer.md) section for more.

## 📦 Installation

```bash
pip install xovis-sdk
```

## 🛠️ Getting Started

1. **Hardware Warmup**: Run `xovis warmup --host <IP>` to sync proprietary schemas from your sensor.
2. **Cloud Sync**: Run `xovis warmup-hub` if you are using Xovis HUB Cloud.
3. **Local Docs**: Explore the [CLI Guide](cli.md) to build your own localized documentation suite.
4. **Architecture**: Review the [Architecture](architecture.md) to understand the SDK's core philosophy.

Dive straight into the [API Reference](api/index.md) for more.
