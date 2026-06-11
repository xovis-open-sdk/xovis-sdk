"""
Xovis SDK - Fleet Orchestration Example

Demonstrates fleet-wide bulk execution and Cloud-to-Edge secure tunneling
for managing massive sensor deployments. Operates within the Control Plane
and State & Topology Plane.
"""

import asyncio
import logging
import os

from xovis.api.device.client import DeviceClient
from xovis.api.device.models import BulkResult
from xovis.api.hub.client import HubClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xovis-fleet")


async def configure_sensor(device: DeviceClient) -> str:
    """
    Business logic to be mapped concurrently across each sensor in the fleet.
    This executes seamlessly through a secure Cloud-to-Edge proxy tunnel using
    intercepted OAuth2 Auth0 tokens.

    Args:
        device (DeviceClient): The Hub-tunneled device client.

    Returns:
        str: A summary of the processing result.
    """
    # Example: Sync system time and retrieve hardware serial
    info = await device.system.get_info()

    # Configuration mutations can be safely executed here:
    # await device.time.update({"time_zone": "Europe/Zurich"})

    return f"Processed {info.type} (Firmware: {info.sw_version})"


async def main():
    # 1. Load Cloud Credentials
    client_id = os.getenv("XOVIS_HUB_CLIENT_ID", "your_client_id")
    client_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET", "your_client_secret")

    # 2. Define Fleet Scope
    # Client-side filtering protects the event loop from resolving unnecessary payloads
    site_filter = {"customerName": "RetailCorp", "siteName": "Terminal_A"}

    # 3. Connect to Xovis HUB Cloud
    async with HubClient(client_id=client_id, client_secret=client_secret, fleet_filter=site_filter) as hub:
        logger.info(f"Connected to HUB. Filtered fleet size: {len(hub.cache._state.devices)}")

        # 4. Demonstrate Resilient Bulk Execution
        # This maps the callback across all filtered devices via asyncio.gather(return_exceptions=True).
        # It guarantees strict fault isolation; an offline sensor will not crash the orchestration pipeline.
        logger.info("Initiating concurrent fleet configuration...")
        results: dict[str, BulkResult[str]] = await hub.bulk_execute(configure_sensor)

        # 5. Triage Results
        successes = [mac for mac, res in results.items() if res.success]
        failures = [mac for mac, res in results.items() if not res.success]

        logger.info(f"Bulk Execution Complete: {len(successes)} Success, {len(failures)} Failed")

        for mac, res in results.items():
            if res.success:
                logger.info(f" [OK] {mac}: {res.result}")
            else:
                logger.error(f" [ERR] {mac}: {res.error}")


if __name__ == "__main__":
    asyncio.run(main())
