"""
Xovis SDK - Edge Basics Example

Demonstrates baseline connectivity, system identification, offline-first persistence,
and proactive capability probing for local edge sensors. Operates within the
Control Plane and State & Topology Plane.
"""

import asyncio
import logging
import os

from xovis.api.device.client import DeviceClient
from xovis.api.device.models import CacheStrategy

# Standard professional logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xovis-example")


async def main():
    # 1. Load credentials from the environment
    host = os.getenv("XOVIS_SENSOR_HOST", "10.0.0.50")
    pw = os.getenv("XOVIS_SENSOR_PASS", "password")

    # 2. Connect to a DeviceClient using an async context manager
    # We use BACKGROUND_WATCHER to automatically sync state and auto_persist_path
    # to safely serialize the HostStateBucket to disk via non-blocking asynchronous threads.
    # Note: Default username is "admin".
    async with DeviceClient(
        host=host,
        username="admin",
        password=pw,
        cache_strategy=CacheStrategy.BACKGROUND_WATCHER,
        auto_persist_path="./device_state.json",
    ) as device:
        # 3. Read system info and check hardware profile
        info = device.info
        if info:
            logger.info(f"Connected to {info.get('type')} (Firmware: {info.get('fw_version')})")

        # 4. Proactive Capability Probing
        # Spider NUCs lack physical lenses, so we must check before accessing singlesensor properties
        if not device.is_spider and await device.has_analytics:
            # 5. Smart Cache Utilization
            # device.cache.zones.by_name allows instant dot-notation access without network penalties
            zones = device.cache.zones.by_name
            logger.info(f"Discovered {len(device.cache.zones)} zones via Cache")
            for zone_name in dir(zones):
                if not zone_name.startswith("_"):
                    logger.info(f" - Zone: {zone_name}")

        # 6. Smart Resolvers in CRUD Operations
        # The SDK resolves human-readable string names to internal IDs automatically
        logic_name = "Store Entrance"
        try:
            logic = await device.singlesensor.analytics.get_logic(logic_name)
            logger.info(f"Successfully retrieved logic '{logic_name}' (ID: {logic.id})")
        except Exception as e:
            logger.warning(f"Could not retrieve logic '{logic_name}': {e}")

        # 7. XovisTime Parser (Modernized History Queries)
        # The SDK features a high-performance, zero-dependency time parser.
        # It normalizes relative offsets, ISO 8601, and datetime objects.
        if not device.is_spider:
            from datetime import datetime, timedelta

            # Query using relative offsets ('-1h', 'now')
            logger.info("Querying historical counts using relative XovisTime ('-1h')...")
            await device.singlesensor.history.get_counts(start_time="-1h", end_time="now", resolution="60")

            # Query using ISO 8601 strings
            logger.info("Querying historical counts using ISO 8601 XovisTime...")
            await device.singlesensor.history.get_counts(start_time="2024-06-09T00:00:00Z", end_time="now", resolution="60")

            # Query using Python datetime objects
            logger.info("Querying historical counts using Python datetime objects...")
            yesterday = datetime.now() - timedelta(days=1)
            await device.singlesensor.history.get_counts(start_time=yesterday, end_time="now", resolution="60")
        else:
            logger.info("Device is a Spider NUC or lacks an Analytics license. Skipping physical layer interactions.")


if __name__ == "__main__":
    asyncio.run(main())
