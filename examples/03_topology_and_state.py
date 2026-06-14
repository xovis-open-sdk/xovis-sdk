"""
Xovis SDK - Topology and State Example

Demonstrates Layer 2.5 network graph mapping, multisensor context isolation,
and offline state caching for local edge sensors. Operates within the State &
Topology Plane.
"""

import asyncio
import logging
import os

from xovis.api.device.client import DeviceClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("xovis-topology")


async def main():
    host = os.getenv("XOVIS_SENSOR_HOST", "10.0.0.50")
    user = os.getenv("XOVIS_SENSOR_USER", "admin")
    pw = os.getenv("XOVIS_SENSOR_PASS", "password")

    # 1. Connect to a DeviceClient
    async with DeviceClient(host=host, username=user, password=pw) as device:
        # 2. Demonstrate Layer 2.5 Graph Mapping
        # Synchronously cross-references the multisensor cluster with physical network nodes
        logger.info("Generating Multisensor Graph Topology...")
        try:
            graph = await device.topology.get_ms_graph()
            logger.info(f"Master MAC: {graph.master_mac}")
            logger.info(f"Child Nodes Discovered: {len(graph.children)}")
            for mac, ip in graph.ip_map.items():
                logger.info(f" - Node {mac} mapped to IP {ip}")
        except Exception as e:
            logger.warning(f"Could not generate multisensor graph: {e}")

        # 3. Demonstrate Multisensor handling and context isolation
        # multisensors.by_name provides cached access to virtual stitched environments (Multisensors)
        ms_contexts = device.multisensors.by_name
        ms_names = [n for n in dir(ms_contexts) if not n.startswith("_")]

        if ms_names:
            first_ms_name = ms_names[0]
            logger.info(f"Selecting Multisensor Context: {first_ms_name}")

            ms_context = getattr(ms_contexts, first_ms_name)

            # The SDK strictly partitions geometries, agents, and analytics by context
            geometries = await ms_context.scene.get_all_geometries()
            zones = [g for g in geometries.geometries if g.type.name == "ZONE"] if geometries.geometries else []
            logger.info(f"Context '{first_ms_name}' possesses {len(zones)} zones")
        else:
            logger.info("No Multisensor contexts found on this device.")

        # 4. Demonstrate Offline Caching & DX CLI Tooling
        # Exporting the RAM cache to a file for persistent state storage or DX CLI consumption
        export_path = "device_state_export.json"
        device.cache.export_to_file(export_path)
        logger.info(f"Device state exported to {export_path}")

        # NOTE: You can now run the ANSI-color CLI to generate static types for IDE autocompletion:
        # xovis-cli --source device_state_export.json --output src/types.py --dry-run


if __name__ == "__main__":
    asyncio.run(main())
