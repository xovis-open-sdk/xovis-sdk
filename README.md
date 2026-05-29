# Xovis SDK

[![PyPI version](https://badge.fury.io/py/xovis-sdk.svg)](https://badge.fury.io/py/xovis-sdk)
[![npm version](https://badge.fury.io/js/xovis-sdk.svg)](https://badge.fury.io/js/xovis-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance integration SDK for Xovis 3D Sensors and the Xovis HUB infrastructure.

**Compliance Note:** This project is an independent, open-source initiative. It is not officially affiliated with, maintained by, or endorsed by Xovis AG.

## Architecture Overview

Integrating native Xovis DataPush protocols and REST APIs typically requires substantial boilerplate infrastructure. 

This SDK provides a unified, modern, and type-safe abstraction layer for both Python and JavaScript/TypeScript environments. It enables engineers to focus strictly on spatial analytics and downstream integration rather than raw stream parsing and network state management.

### Core Capabilities

* **Device API Interface:** Native programmatic handlers for zone occupancy metrics, line crossing events, and sensor state management.
* **HUB API Integration:** Centralized management for sensor fleets, historical data extraction, and automated provisioning workflows.
* **DataPush Ingestion Sinks:** Pre-configured MQTT, Webhook, and WebSocket receivers designed to autonomously capture and deserialize high-frequency live telemetry streams.
* **Modern Concurrency:** Architected with tree-shakable ES Modules for JavaScript/TypeScript and native asynchronous (`async/await`) event loops for Python.

## Installation

*Note: Version 0.0.1 is currently deployed as a registry placeholder. The full v1.0 release is actively being ported to this repository.*

**Python (Data Science & Backend Infrastructure):**
```bash
pip install xovis-sdk
```

**Node.js / TypeScript (Frontend & Dashboards):**

```bash
npm install xovis-sdk
```

## API Preview

The following demonstrates the targeted syntax for edge-sensor initialization and live stream ingestion upon the v1.0 release:

```python
from src.xovis import XovisDevice

# Initialize connection to the edge sensor
sensor = XovisDevice("192.168.1.50", "admin", "password")


# Subscribe to the high-frequency coordinate stream
@sensor.on_track_update
def handle_person(track):
    print(f"Track ID: {track.id} | Velocity: {track.speed} m/s")


# Execute the asynchronous listening loop
sensor.start_listening()
```

## Contributing

We welcome contributions from users, developers, and the broader engineering community. Official guidelines for pull requests, issue tracking, and architectural discussions will be published shortly.
