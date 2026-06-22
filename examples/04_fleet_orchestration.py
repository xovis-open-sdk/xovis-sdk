"""
Xovis SDK - Fleet Orchestration Example

Demonstrates fleet-wide bulk execution and Cloud-to-Edge secure tunneling
for managing massive sensor deployments using the SDK-native Fleet Buckets.
Operates within the Control Plane and State & Topology Plane.
"""

import asyncio
import logging
import os

from xovis.api.fleet import DeviceGroup, HubFleetDirectory
from xovis.api.hub.client import HubClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xovis-fleet")

async def main():
    # 1. Load Cloud Credentials
    client_id = os.getenv("XOVIS_HUB_CLIENT_ID", "your_client_id")
    client_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET", "your_client_secret")

    # 2. Connect to Xovis HUB Cloud
    async with HubClient(client_id=client_id, client_secret=client_secret) as hub:
        logger.info("Connected to HUB. Building IDE-autosuggested directory...")
        
        # 3. Build the Fleet Directory
        directory = await HubFleetDirectory.from_hub(hub)
        
        # 4. Filter and Group by Customer (e.g., 'RetailCorp')
        if hasattr(directory.by_customer, "RetailCorp"):
            retail_devices = directory.by_customer.RetailCorp
            logger.info(f"Filtered fleet size: {len(retail_devices)} for RetailCorp")

            # 5. Create a DeviceGroup Fleet Bucket
            # This implicitly uses the Hub for proxy tunneling so no local password is required
            grp = DeviceGroup.from_directory_nodes(
                name="RetailCorp_Rollout",
                nodes=retail_devices,
                hub_client=hub
            )

            # 6. Demonstrate Resilient Bulk Execution
            # This broadcasts the command concurrently across all filtered devices.
            # It guarantees strict fault isolation; an offline sensor will not crash the orchestration pipeline.
            logger.info("Initiating concurrent fleet configuration...")
            result = await grp.system.get_info()

            # 7. Triage Results
            logger.info(f"Bulk Execution Complete: {len(result.successes)} Success, {len(result.exceptions)} Failed")

            for device_client, info in result.successes.items():
                logger.info(f" [OK] {device_client.host}: Processed {info.type} (Firmware: {info.fw_version})")

            for device_client, error in result.exceptions.items():
                logger.error(f" [ERR] {device_client.host}: {error}")
        else:
            logger.info("Customer 'RetailCorp' not found in the Hub fleet directory.")

if __name__ == "__main__":
    asyncio.run(main())
