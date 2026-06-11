"""
Xovis SDK - HUB Synchronization Utility

This module provides the `HubSyncer`, a utility designed to synchronize
cloud-level resources from the Xovis HUB Cloud to the local environment.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from xovis.api.hub.client import HubClient

logger = logging.getLogger(__name__)


class HubSyncer:
    """
    Orchestrates the retrieval of cloud-specific resources from Xovis HUB.

    This utility is used during initial setup to populate the '_local_ressources/'
    directory with HUB OpenAPI schemas and fleet state information.
    """

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, base_url: str = "https://api.xovis.cloud"):
        """
        Initializes the HubSyncer.

        Args:
            client_id (Optional[str]): OAuth2 Client ID.
            client_secret (Optional[str]): OAuth2 Client Secret.
            base_url (str): Base URL for the Xovis HUB Cloud.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.resource_dir = Path("_local_ressources").resolve()

    async def warmup(self, force: bool = False) -> bool:
        """
        Performs a full synchronization of HUB resources.

        Args:
            force (bool): If True, overwrites existing local resources.

        Returns:
            bool: True if synchronization was successful.
        """
        logger.info("Initiating Xovis HUB warmup...")
        self.resource_dir.mkdir(exist_ok=True)

        try:
            async with HubClient(client_id=self.client_id, client_secret=self.client_secret, base_url=self.base_url) as client:
                # 1. Fetch HUB OpenAPI Schemas
                await self._fetch_hub_openapi(client, force)

                # 2. Fetch Fleet State
                state_path = self.resource_dir / "hub_fleet_state.json"
                logger.info(f"Exporting HUB fleet state to {state_path}...")
                await client.cache.sync()
                client.cache.export_to_file(str(state_path))

                logger.info("Xovis HUB warmup completed successfully.")
                return True
        except Exception as e:
            logger.error(f"Xovis HUB warmup failed: {e}")
            return False

    async def _fetch_hub_openapi(self, client: HubClient, force: bool):
        """Fetches the HUB OpenAPI schemas."""
        # Official HUB OpenAPI endpoints
        # We fetch the public specifications for the two primary modules managed by the SDK
        # Note: The 'notification' endpoint is intentionally omitted as it is currently unused.
        modules = {
            "device-management": "/device-management/openapi_public_v1.json",
            "license": "/license/openapi_public_v1.json",
        }

        for module_name, endpoint in modules.items():
            target = self.resource_dir / f"HUB-{module_name}.json"

            if target.exists() and not force:
                logger.debug(f"HUB schema {module_name} already exists. Skipping.")
                continue

            try:
                # We use the internal http_client of the HubClient
                response = await client._http_client.get(endpoint)
                if response.status_code == 200:
                    schema_data = response.json()
                    version = schema_data.get("info", {}).get("version", "v1").replace(".", "-")

                    # Versioned target: e.g. HUB-device-management_v1.json
                    versioned_target = self.resource_dir / f"HUB-{module_name}_{version}.json"
                    versioned_target.write_text(response.text)
                    logger.info(f"Saved versioned HUB OpenAPI schema to {versioned_target}")

                    # Latest target: e.g. HUB-device-management.json
                    target.write_text(response.text)
                    logger.info(f"Saved HUB OpenAPI schema to {target}")
                else:
                    logger.debug(f"HUB endpoint {endpoint} returned {response.status_code}")
            except Exception as e:
                logger.debug(f"Could not fetch HUB schema from {endpoint}: {e}")

        logger.info("HUB OpenAPI synchronization complete.")
