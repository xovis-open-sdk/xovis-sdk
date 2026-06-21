# API Reference

The Xovis SDK provides multiple ways to interact with the hardware and cloud infrastructure.

!!! tip "Xovis HUB Pro"
    For enterprise-scale fleet orchestration via the `HubClient`, a **Xovis HUB Pro** subscription is recommended to ensure stable rate limits for high-concurrency operations.
    <br><br>**Compliance Note:** This project is an independent, open-source initiative. It is not officially affiliated with, maintained by, or endorsed by Xovis AG.

## 📡 Device & Hub API (OpenAPI)

The raw hardware and cloud APIs are documented via interactive Scalar references.

- [Xovis Device API (Scalar)](reference.md)
- [Xovis Hub Device API (Scalar)](hub_device_ref.md)
- [Xovis Hub License API (Scalar)](hub_license_ref.md)

## 🐍 Python SDK Reference

The Python SDK is organized according to the **quadrifurcated architecture**.

### Planes
- [**The Data Plane**](python/datapush.md): High-frequency telemetry ingestion.
- [**The Control Plane**](python/device.md): Low-frequency REST API wrappers for edge sensors.
- [**The Hub Plane**](python/hub.md): Cloud-scale fleet management.
- [**The Agentic Layer**](python/skills.md): AI Skillsets and MCP toolkits.

## 🤖 Model Context Protocol (MCP)

The Xovis SDK provides a native MCP server for seamless AI integration.

| **Discovery** | **Installation** |
|:---:|:---:|
| [![MCP Ready](https://img.shields.io/badge/MCP-Ready-5B32A8.svg?logo=server&logoColor=white)](https://modelcontextprotocol.io/) | [![Smithery Install](https://img.shields.io/badge/Smithery-Install-orange.svg)](https://smithery.ai/server/xovis-sdk) |

- **Manual Setup:** See [MCP Configuration](../ai/mcp.md#deployment-configuration)

For a detailed module-level overview, see the [Core SDK](python/core.md) documentation.
