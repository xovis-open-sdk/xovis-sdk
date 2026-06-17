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
    the '_local_resources/' directory with the required schemas for the
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
        self.resource_dir = Path("_local_resources").resolve()

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
                await self._fetch_openapi(client, force)

                await self._fetch_datapush_schemas(client, force)

                await self._fetch_datapush_samples(client, force)

                states_dir = self.resource_dir / "states"
                states_dir.mkdir(parents=True, exist_ok=True)

                state_path = states_dir / f"state_{self.host.replace('.', '_')}.json"
                logger.info(f"Exporting host state to {state_path}...")
                await client.cache.sync()
                state = client.cache._state
                state_json = state.model_dump_json(indent=2)
                state_path.write_text(state_json)

                unified_state_path = states_dir / "device_state.json"
                unified_state_path.write_text(state_json)

                logger.info("Hardware warmup completed successfully.")
                return True
        except Exception as e:
            logger.error(f"Hardware warmup failed: {e}")
            return False

    async def _fetch_openapi(self, client: DeviceClient, force: bool):
        """Fetches the OpenAPI v5 schema from the device."""
        fw_version = client.fw_version.replace(".", "-") if hasattr(client, "fw_version") else "unknown"
        target_dir = self.resource_dir / "schemas" / fw_version
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "api.yaml"

        fallback_dir = self.resource_dir / "schemas"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        latest_target = fallback_dir / "api.yaml"

        if target.exists() and not force:
            logger.info(f"OpenAPI schema for version {fw_version} already exists locally. Skipping.")
            return

        logger.info(f"Fetching OpenAPI schema for version {fw_version} from device...")
        endpoint = "/swagger/api.yaml"

        try:
            response = await client._http_client.get(endpoint)
            if response.status_code == 200:
                target.write_text(response.text)
                logger.info(f"Saved versioned OpenAPI schema to {target}")

                latest_target.write_text(response.text)

                logger.info("OpenAPI synchronization complete.")
            else:
                logger.warning(f"Endpoint {endpoint} returned status {response.status_code}. Could not fetch OpenAPI schema.")
        except Exception as e:
            logger.error(f"Could not fetch from {endpoint}: {e}")

    async def _fetch_datapush_schemas(self, client: DeviceClient, force: bool) -> None:
        """Fetches all DataPush JSON schemas concurrently from the device.

        Queries the individual schemas (live, logics, status, wifibt) and
        persists them to the resource directory in a non-blocking manner.

        Args:
            client (DeviceClient): The authenticated connection client to the device.
            force (bool): If True, overwrites existing local schema files.
        """
        fw_version = client.fw_version.replace(".", "-") if hasattr(client, "fw_version") else "unknown"
        target_dir = self.resource_dir / "schemas" / fw_version
        target_dir.mkdir(parents=True, exist_ok=True)

        schemas = {
            "live": "datapush_live.json",
            "logics": "datapush_logics.json",
            "status": "datapush_status.json",
            "wifibt": "datapush_wifibt.json",
        }

        headers = {
            "accept": "application/json",
            "X-Requested-With": "XmlHttpRequest",
        }

        async def fetch_and_save(schema_type: str, filename: str) -> None:
            target = target_dir / filename
            if target.exists() and not force:
                logger.debug(f"DataPush schema '{schema_type}' already exists locally. Skipping.")
                return

            endpoint = f"/api/v5/schemas/datapush/{schema_type}"
            try:
                response = await client._http_client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    await asyncio.to_thread(target.write_text, response.text, encoding="utf-8")
                    logger.info(f"Successfully synchronized schema: {filename}")
                else:
                    logger.warning(f"Failed fetching schema '{schema_type}' (status {response.status_code}) from {endpoint}")
            except Exception as exc:
                logger.error(f"Error requesting schema '{schema_type}' from {endpoint}: {exc}")

        tasks = [fetch_and_save(schema_type, filename) for schema_type, filename in schemas.items()]
        await asyncio.gather(*tasks)

    async def _fetch_datapush_samples(self, client: DeviceClient, force: bool):
        """Generates or fetches sample DataPush payloads."""
        samples_dir = self.resource_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        samples = ["live.json", "logic.json", "status.json", "wifibt.json"]

        for sample in samples:
            target = samples_dir / sample
            if target.exists() and not force:
                continue

            logger.debug(f"Ensuring DataPush sample exists: {sample}")
