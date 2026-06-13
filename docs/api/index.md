# API Reference

The Xovis SDK provides multiple ways to interact with the hardware and cloud infrastructure.

## 📡 Edge & Hub API (OpenAPI)

The raw hardware and cloud APIs are documented via interactive Scalar references.

- [Xovis Edge API (Scalar)](reference.md)
- [Xovis Hub Device API (Scalar)](hub_device_ref.md)
- [Xovis Hub License API (Scalar)](hub_license_ref.md)

## 🐍 Python SDK Reference

The Python SDK is organized according to the **quadrifurcated architecture**.

### Planes
- [**The Data Plane**](python/datapush.md): High-frequency telemetry ingestion.
- [**The Control Plane**](python/device.md): Low-frequency REST API wrappers for edge sensors.
- [**The Hub Plane**](python/hub.md): Cloud-scale fleet management.
- [**The Agentic Layer**](python/skills.md): AI Skillsets and MCP toolkits.

For a detailed module-level overview, see the [Core SDK](python/core.md) documentation.
