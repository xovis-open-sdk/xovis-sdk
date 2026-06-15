"""
Xovis SDK - Hardware Synchronization Utility

This module provides the `HardwareSyncer`, a utility designed to bridge the gap
between the SDK and physical hardware by fetching OpenAPI schemas, DataPush
payload definitions, and other localized resources directly from a sensor.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from xovis.api.device.client import DeviceClient

logger = logging.getLogger(__name__)


class HardwareSyncer:
    """
    Orchestrates the retrieval of hardware-specific resources from Xovis sensors.

    This utility is primarily used during initial setup ('warmup') to populate
    the '_local_ressources/' directory with the required schemas for the
    'xovis-cli' and the Model Context Protocol (MCP) server.
    """

    def __init__(self, host: str, username: str = "admin", password: str = "pass"):
        """
        Initializes the HardwareSyncer.

        Args:
            host (str): IP address or hostname of the Xovis sensor.
            username (str): Authentication username.
            password (str): Authentication password.
        """
        self.host = host
        self.username = username
        self.password = password
        self.resource_dir = Path("_local_ressources").resolve()

    async def warmup(self, force: bool = False) -> bool:
        """
        Performs a full synchronization of hardware resources.

        Args:
            force (bool): If True, overwrites existing local resources.

        Returns:
            bool: True if synchronization was successful.
        """
        logger.info(f"Initiating hardware warmup for {self.host}...")
        self.resource_dir.mkdir(exist_ok=True)

        try:
            async with DeviceClient(self.host, self.username, self.password) as client:
                # 1. Fetch OpenAPI Schema
                await self._fetch_openapi(client, force)

                # 2. Fetch DataPush Payloads (mocked or sampled if supported)
                await self._fetch_datapush_samples(client, force)

                # 3. Fetch Host State for Type Generation
                state_path = self.resource_dir / f"state_{self.host.replace('.', '_')}.json"
                logger.info(f"Exporting host state to {state_path}...")
                await client.cache.sync()
                state = client.cache._state
                state_json = state.model_dump_json(indent=2)
                state_path.write_text(state_json)

                # Also save unified device_state.json in resource_dir
                unified_state_path = self.resource_dir / "device_state.json"
                unified_state_path.write_text(state_json)

                logger.info("Hardware warmup completed successfully.")
                return True
        except Exception as e:
            logger.error(f"Hardware warmup failed: {e}")
            return False

    async def _fetch_openapi(self, client: DeviceClient, force: bool):
        """Fetches the OpenAPI v5 schema from the device."""
        fw_version = client.fw_version.replace(".", "-") if hasattr(client, "fw_version") else "unknown"
        target = self.resource_dir / f"api_{fw_version}.yaml"
        latest_target = self.resource_dir / "api.yaml"

        if target.exists() and not force:
            logger.info(f"OpenAPI schema for version {fw_version} already exists locally. Skipping.")
            return

        logger.info(f"Fetching OpenAPI schema for version {fw_version} from device...")
        endpoint = "/swagger/api.yaml"

        try:
            response = await client._http_client.get(endpoint)
            if response.status_code == 200:
                # Save with version-specific name
                target.write_text(response.text)
                logger.info(f"Saved versioned OpenAPI schema to {target}")

                # Also save/overwrite the latest 'api.yaml' for documentation compatibility
                latest_target.write_text(response.text)

                logger.info("OpenAPI synchronization complete.")
            else:
                logger.warning(f"Endpoint {endpoint} returned status {response.status_code}. Could not fetch OpenAPI schema.")
        except Exception as e:
            logger.error(f"Could not fetch from {endpoint}: {e}")

    async def _fetch_datapush_samples(self, client: DeviceClient, force: bool):
        """Generates or fetches sample DataPush payloads."""
        samples = ["live.json", "logic.json", "status.json", "wifibt.json"]

        for sample in samples:
            target = self.resource_dir / sample
            if target.exists() and not force:
                continue

            # For now, we use baseline defaults if we can't fetch live ones
            # In a real scenario, we might trigger a temporary DataPush agent
            # to capture a single frame.
            logger.debug(f"Ensuring DataPush sample exists: {sample}")
            # Placeholder for future live capture logic
