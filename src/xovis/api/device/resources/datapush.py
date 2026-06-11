"""
Xovis SDK - DataPush Management Resource

Operates within the Control Plane.
Provides the implementation for managing high-frequency telemetry pipelines
(DataPush agents and connections) on local edge sensors. Integrates advanced
trigger mechanics for autonomous data recovery and fault remediation.
"""

import asyncio
import uuid
from typing import TYPE_CHECKING, Any, Optional, Union

from xovis.api.core.exceptions import MultipleResourcesFoundError, ResourceNotFoundError
from xovis.models.device import (
    DataPushAgent,
    DataPushAgentCollection,
    DataPushConnection,
    DataPushConnectionCollection,
    DataPushStatus,
    DataPushStatusCollection,
    DataPushTestResponse,
    DataPushTriggerConfig,
    DataPushTriggerInfo,
)
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient
    from xovis.models.device_auto.versions.v5_9_11 import LegacyConfigGet, LegacyConfigPut


def _recursive_none_filter(data: Any) -> Any:
    """Recursively removes None values from dictionaries and lists."""
    if isinstance(data, dict):
        return {k: _recursive_none_filter(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [_recursive_none_filter(v) for v in data if v is not None]
    return data


class DataPushManager:
    """
    Manages DataPush pipelines (Agents and Connections) on a Xovis device.

    This manager provisions the telemetry datapush that feed downstream
    engines. It supports full CRUD operations, connection diagnostics, and
    crucially, autonomous data recovery triggers to maintain zero-downtime SLAs.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the DataPushManager.

        Args:
            client (DeviceClient): The parent device client instance.
            target_id (Optional[str]): The multisensor target ID, if applicable.
                If None, defaults to the physical singlesensor context.
        """
        self._client = client
        self._http = client._http_client
        self.target_id = target_id

    @property
    def models(self) -> Any:
        """
        Returns the strictly validated Pydantic models for the current firmware.

        Returns:
            Any: The collection of auto-generated Pydantic V2 models
                synchronized with the current device firmware.
        """
        return self._client.models if self._client else stable_models

    def _resolve_path(self) -> str:
        """
        Resolves the base API path based on the current isolated context.

        Returns:
            str: The resolved API endpoint path.
        """
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}/data/push"
        return "/api/v5/singlesensor/data/push"

    async def _resolve_agent_id(self, id_or_name: Union[str, uuid.UUID, int]) -> str:
        """
        Resolves an agent ID from either a UUID string, integer, or human-readable name.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The ID or name of the agent.

        Returns:
            str: The resolved agent ID string.

        Raises:
            ResourceNotFoundError: If the name cannot be resolved in the cache.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        if isinstance(id_or_name, int) or (isinstance(id_or_name, str) and id_or_name.isdigit()):
            return str(id_or_name)

        try:
            return str(uuid.UUID(str(id_or_name)))
        except ValueError:
            pass

        # Use cache for name resolution
        multisensors = self._client.cache.multisensors
        if self.target_id:
            target_str = str(self.target_id)
            if target_str not in (multisensors._items if hasattr(multisensors, "_items") else multisensors):
                # Proactive sync of multisensors if context is missing
                await self._client.multisensors.sync()
            context = multisensors[target_str]
        else:
            context = self._client.cache.singlesensor

        if context.agents is None or not any(a.name == id_or_name for a in context.agents):
            await self.get_all_agents()

        matches = [a for a in context.agents if a.name == id_or_name]

        if not matches:
            raise ResourceNotFoundError(f"No agent found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} agents named '{id_or_name}'. Use exact ID.")
        return str(matches[0].id)

    async def _resolve_connection_id(self, id_or_name: Union[str, uuid.UUID, int]) -> str:
        """
        Resolves a connection ID from either a UUID string, integer, or human-readable name.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The ID or name of the connection.

        Returns:
            str: The resolved connection ID string.

        Raises:
            ResourceNotFoundError: If the name cannot be resolved.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        if isinstance(id_or_name, int) or (isinstance(id_or_name, str) and id_or_name.isdigit()):
            return str(id_or_name)

        try:
            return str(uuid.UUID(str(id_or_name)))
        except ValueError:
            pass

        # Use cache for name resolution
        multisensors = self._client.cache.multisensors
        if self.target_id:
            target_str = str(self.target_id)
            if target_str not in (multisensors._items if hasattr(multisensors, "_items") else multisensors):
                # Proactive sync of multisensors if context is missing
                await self._client.multisensors.sync()
            context = multisensors[target_str]
        else:
            context = self._client.cache.singlesensor

        # Proactive sync if cache is empty or name is missing
        if not context.connections or not any(c.name == id_or_name for c in context.connections):
            await self.get_all_connections()

        matches = [c for c in context.connections if c.name == id_or_name]

        if not matches:
            raise ResourceNotFoundError(f"No connection found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} connections named '{id_or_name}'.")
        return str(matches[0].id)

    async def _pacing_delay(self) -> None:
        """
        Implements intra-mutation pacing to prevent sensor configuration OOM or service crashes.

        Mandatory for FW 5.9.2+ where rapid REST mutations can lead to internal service
        desynchronization and subsequent hardware reboots.
        """
        await asyncio.sleep(2.0)

    # --- AGENTS ---
    async def get_all_agents(self, volatile: bool = False) -> DataPushAgentCollection:
        """
        Retrieves all configured DataPush agents from the sensor.

        Args:
            volatile (bool): If true, returns volatile agents stored in RAM.
                Defaults to False.

        Returns:
            DataPushAgentCollection: A validated collection of agent configurations.
        """
        params = {"volatile": "true" if volatile else "false"}
        response = await self._http.get(f"{self._resolve_path()}/agents", params=params)
        collection = DataPushAgentCollection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        context.agents = collection.agents

        return collection

    async def create_agent(self, agent: DataPushAgent, volatile: bool = False, id_mode: str = "SERVER") -> DataPushAgent:
        """
        Provisions a new DataPush agent telemetry stream.

        Args:
            agent (DataPushAgent): The validated agent configuration to create.
            volatile (bool): If true, creates a volatile agent in RAM (does not survive reboot).
            id_mode (str): The ID assignment mode ('SERVER' or 'CLIENT').

        Returns:
            DataPushAgent: The actively provisioned agent configuration.
        """
        await self._pacing_delay()
        params = {"volatile": "true" if volatile else "false", "id_mode": id_mode}
        # Use exclude_unset=True to allow sending explicit nulls if required by hardware
        # Use _recursive_none_filter to remove unwanted nulls that break schema validation
        payload = _recursive_none_filter(agent.model_dump(by_alias=True, exclude_unset=True, mode="json"))
        # Force enabled to True in payload if it is unset in the model to ensure activation.
        # Xovis firmware defaults new agents to deactivated if this field is missing.
        if "enabled" not in payload:
            payload["enabled"] = True

        response = await self._http.post(f"{self._resolve_path()}/agents", params=params, json=payload)
        created_agent = DataPushAgent.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.agents is not None:
            # Proactive sync if cache is empty to avoid list mismatch
            if not context.agents:
                await self.get_all_agents()

            # Replace or append
            new_agents = [a for a in context.agents if str(a.id) != str(created_agent.id)]
            new_agents.append(created_agent)
            context.agents = new_agents

        return created_agent

    async def delete_all_agents(self, volatile: bool = False) -> None:
        """
        Destructively removes all DataPush agents from the context.

        Args:
            volatile (bool): If true, deletes only volatile agents stored in RAM.
                Defaults to False.
        """
        await self._pacing_delay()
        params = {"volatile": "true" if volatile else "false"}
        await self._http.delete(f"{self._resolve_path()}/agents", params=params)

    async def get_agent(self, id_or_name: Union[str, uuid.UUID, int]) -> DataPushAgent:
        """
        Retrieves the exact configuration of a specific DataPush agent.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The ID or logical name of the agent.

        Returns:
            DataPushAgent: The validated agent configuration.
        """
        agent_id = await self._resolve_agent_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/agents/{agent_id}")
        return DataPushAgent.model_validate(response.json())

    async def update_agent(self, id_or_name: Union[str, uuid.UUID, int], agent: DataPushAgent) -> DataPushAgent:
        """
        Replaces an existing DataPush agent configuration entirely.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The target agent.
            agent (DataPushAgent): The full updated agent configuration payload.

        Returns:
            DataPushAgent: The successfully updated agent configuration.
        """
        await self._pacing_delay()
        agent_id = await self._resolve_agent_id(id_or_name)
        # Use exclude_unset=True to allow sending explicit nulls if required by hardware
        # Use _recursive_none_filter to remove unwanted nulls that break schema validation
        payload = _recursive_none_filter(agent.model_dump(by_alias=True, exclude_unset=True, mode="json"))
        response = await self._http.put(f"{self._resolve_path()}/agents/{agent_id}", json=payload)
        updated_agent = DataPushAgent.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.agents is not None:
            new_agents = [a for a in context.agents if str(a.id) != str(updated_agent.id)]
            new_agents.append(updated_agent)
            context.agents = new_agents

        return updated_agent

    async def patch_agent(self, id_or_name: Union[str, uuid.UUID, int], updates: dict[str, Any]) -> DataPushAgent:
        """
        Applies a partial update to an existing DataPush agent.

        Crucial for autonomous agents modifying specific parameters (e.g., retry logic)
        without risking overwriting the entire complex payload.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The target agent.
            updates (Dict[str, Any]): A partial dictionary of modifications.

        Returns:
            DataPushAgent: The updated agent configuration.
        """
        await self._pacing_delay()
        agent_id = await self._resolve_agent_id(id_or_name)
        response = await self._http.patch(f"{self._resolve_path()}/agents/{agent_id}", json=updates)
        updated_agent = DataPushAgent.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.agents is not None:
            new_agents = [a for a in context.agents if str(a.id) != str(updated_agent.id)]
            new_agents.append(updated_agent)
            context.agents = new_agents

        return updated_agent

    async def delete_agent(self, id_or_name: Union[str, uuid.UUID, int]) -> None:
        """Removes a specific DataPush agent."""
        await self._pacing_delay()
        agent_id = await self._resolve_agent_id(id_or_name)
        await self._http.delete(f"{self._resolve_path()}/agents/{agent_id}")

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.agents is not None:
            context.agents = [a for a in context.agents if str(a.id) != str(agent_id)]

    async def get_agents_status(self, volatile: bool = False) -> DataPushStatusCollection:
        """
        Retrieves the runtime networking status for all DataPush agents.

        Args:
            volatile (bool): If true, retrieves status for volatile agents.
                Defaults to False.

        Returns:
            DataPushStatusCollection: Contains transmit speeds, dropped packet counts,
                and HTTP/MQTT failure codes across the fleet.
        """
        params = {"volatile": "true" if volatile else "false"}
        response = await self._http.get(f"{self._resolve_path()}/agents/status", params=params)
        return DataPushStatusCollection.model_validate(response.json())

    async def get_agent_status(self, id_or_name: Union[str, uuid.UUID, int]) -> DataPushStatus:
        """
        Retrieves the runtime status for a specific DataPush agent.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The ID or logical name
                of the target agent.

        Returns:
            DataPushStatus: The runtime status of the specific agent.
        """
        agent_id = await self._resolve_agent_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/agents/{agent_id}/status")
        return DataPushStatus.model_validate(response.json())

    # --- AGENT TRIGGERS (DATA RECOVERY) ---
    async def trigger_agent_push(self, id_or_name: Union[str, uuid.UUID, int], trigger_config: DataPushTriggerConfig) -> DataPushTriggerInfo:
        """
        Forces the agent to immediately flush or recover data.

        Essential for Autonomous Maintenance. If a sensor was offline, an agent can
        use a 'TIME_RANGE' trigger configuration to datapush the missing edge-cached data
        up to the downstream processing engine.

        NOTE: 'STATUS' and 'RECORDING' agents do not support manual retriggering.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The target agent.
            trigger_config (DataPushTriggerConfig): Validated Pydantic configuration defining
                'ALL', 'LAST_PACKAGE', or 'TIME_RANGE' (with XovisTime) rules.

        Returns:
            DataPushTriggerInfo: The active trigger execution status.
        """
        await self._pacing_delay()

        # PROACTIVE BLOCK: Status and Recording agents do not support retriggering.
        # This prevents hardware-level rejections or instability.
        from xovis.models.device import DataPushType

        agent = await self.get_agent(id_or_name)
        if agent.type in (DataPushType.STATUS, DataPushType.RECORDING):
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Manual retriggering is not supported for agent type: {agent.type}")
            # We return an IDLE status instead of raising to avoid breaking autonomous loops
            return DataPushTriggerInfo(status="IDLE", trigger_config=trigger_config)

        agent_id = agent.id
        # Pydantic V2 mode="json" ensures XovisTime in 'time_from' and 'time_to'
        # are correctly normalized to Unix milliseconds during serialization.
        payload = trigger_config.model_dump(by_alias=True, exclude_unset=True, mode="json")
        response = await self._http.post(f"{self._resolve_path()}/agents/{agent_id}/trigger", json=payload)

        # FIRMWARE BUG WORKAROUND:
        # Some firmware versions return a list containing the status object instead of the object itself.
        # Or a list of strings for errors.
        # Or the trigger config itself instead of status (seen on some Multisensor firmware).
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                data = data[0]

        # If the firmware returned the config instead of status, synthesize an IDLE status
        if isinstance(data, dict) and "status" not in data and "type" in data:
            data = {"status": "IDLE", "trigger_config": data}

        return DataPushTriggerInfo.model_validate(data)

    async def get_agent_trigger_status(self, id_or_name: Union[str, uuid.UUID, int]) -> DataPushTriggerInfo:
        """
        Polls the execution state of an actively running trigger datapush (BUSY or IDLE).
        """
        agent_id = await self._resolve_agent_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/agents/{agent_id}/trigger")

        # FIRMWARE BUG WORKAROUND:
        # Some firmware versions return a list containing the status object instead of the object itself.
        # Or a list of strings for errors.
        # Or the trigger config itself instead of status (seen on some Multisensor firmware).
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                data = data[0]

        # If the firmware returned the config instead of status, synthesize an IDLE status
        if isinstance(data, dict) and "status" not in data and "type" in data:
            data = {"status": "IDLE", "trigger_config": data}

        return DataPushTriggerInfo.model_validate(data)

    async def abort_agent_trigger(self, id_or_name: Union[str, uuid.UUID, int]) -> None:
        """Aborts a currently running trigger datapush."""
        await self._pacing_delay()
        agent_id = await self._resolve_agent_id(id_or_name)
        await self._http.delete(f"{self._resolve_path()}/agents/{agent_id}/trigger")

    # --- CONNECTIONS ---
    async def get_all_connections(self, volatile: bool = False) -> DataPushConnectionCollection:
        """Retrieves all defined network targets (Connections) for agents."""
        params = {"volatile": "true" if volatile else "false"}
        response = await self._http.get(f"{self._resolve_path()}/connections", params=params)
        collection = DataPushConnectionCollection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        context.connections = collection.connections

        return collection

    async def create_connection(self, connection: DataPushConnection, volatile: bool = False, id_mode: str = "SERVER") -> DataPushConnection:
        """Provisions a new network target (HTTP, MQTT, TCP, etc.)."""
        await self._pacing_delay()
        params = {"volatile": "true" if volatile else "false", "id_mode": id_mode}
        # Use exclude_unset=True to avoid stripping mandatory nulls for firmware
        # Use _recursive_none_filter to remove unwanted nulls that break schema validation
        payload = _recursive_none_filter(connection.model_dump(by_alias=True, exclude_unset=True, mode="json"))
        response = await self._http.post(f"{self._resolve_path()}/connections", params=params, json=payload)
        created_conn = DataPushConnection.model_validate(response.json())

        # Sync cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.connections is not None:
            # Proactive sync if cache is empty to avoid list mismatch
            if not context.connections:
                await self.get_all_connections()

            new_conns = [c for c in context.connections if str(c.id) != str(created_conn.id)]
            new_conns.append(created_conn)
            context.connections = new_conns

        return created_conn

    async def delete_all_connections(self, volatile: bool = False) -> None:
        """
        Destructively removes all connections from the context.

        Args:
            volatile (bool): If true, deletes only volatile connections.
                Defaults to False.
        """
        await self._pacing_delay()
        params = {"volatile": "true" if volatile else "false"}
        await self._http.delete(f"{self._resolve_path()}/connections", params=params)

    async def get_connection(self, id_or_name: Union[str, uuid.UUID, int]) -> DataPushConnection:
        """
        Retrieves a specific connection configuration.

        Args:
            id_or_name (Union[str, uuid.UUID, int]): The ID or logical name
                of the target connection.

        Returns:
            DataPushConnection: The validated connection configuration.
        """
        conn_id = await self._resolve_connection_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/connections/{conn_id}")
        return DataPushConnection.model_validate(response.json())

    async def update_connection(self, id_or_name: Union[str, uuid.UUID, int], connection: DataPushConnection) -> DataPushConnection:
        """Replaces an existing connection configuration entirely."""
        await self._pacing_delay()
        conn_id = await self._resolve_connection_id(id_or_name)
        # Use exclude_unset=True to avoid stripping mandatory nulls for firmware
        # Use _recursive_none_filter to remove unwanted nulls that break schema validation
        payload = _recursive_none_filter(connection.model_dump(by_alias=True, exclude_unset=True, mode="json"))
        response = await self._http.put(f"{self._resolve_path()}/connections/{conn_id}", json=payload)
        updated_conn = DataPushConnection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.connections is not None:
            new_conns = [c for c in context.connections if str(c.id) != str(updated_conn.id)]
            new_conns.append(updated_conn)
            context.connections = new_conns

        return updated_conn

    async def patch_connection(self, id_or_name: Union[str, uuid.UUID, int], updates: dict[str, Any]) -> DataPushConnection:
        """
        Applies a partial update to an existing connection.
        Useful for rotating passwords or updating host URIs autonomously.
        """
        await self._pacing_delay()
        conn_id = await self._resolve_connection_id(id_or_name)
        response = await self._http.patch(f"{self._resolve_path()}/connections/{conn_id}", json=updates)
        updated_conn = DataPushConnection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.connections is not None:
            new_conns = [c for c in context.connections if str(c.id) != str(updated_conn.id)]
            new_conns.append(updated_conn)
            context.connections = new_conns

        return updated_conn

    async def delete_connection(self, id_or_name: Union[str, uuid.UUID, int]) -> None:
        """Removes a specific connection."""
        await self._pacing_delay()
        conn_id = await self._resolve_connection_id(id_or_name)
        await self._http.delete(f"{self._resolve_path()}/connections/{conn_id}")

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        if context.connections is not None:
            context.connections = [c for c in context.connections if str(c.id) != str(conn_id)]

    async def test_connection(self, id_or_name: Union[str, uuid.UUID, int]) -> DataPushTestResponse:
        """
        Fires a dummy payload through the connection to verify network egress.
        Crucial for pre-flight validation by autonomous deployment agents.
        """
        conn_id = await self._resolve_connection_id(id_or_name)
        response = await self._http.post(f"{self._resolve_path()}/connections/{conn_id}/test")
        return DataPushTestResponse.model_validate(response.json())

    # --- LEGACY CONFIGURATION ---
    async def get_legacy_config(self) -> "LegacyConfigGet":
        """Retrieves legacy conversion settings for backward-compatible systems."""
        response = await self._http.get(f"{self._resolve_path()}/legacy")
        return self.models.LegacyConfigGet.model_validate(response.json())

    async def update_legacy_config(self, config: "LegacyConfigPut") -> "LegacyConfigGet":
        """Updates legacy conversion settings."""
        await self._pacing_delay()
        payload = _recursive_none_filter(config.model_dump(by_alias=True, exclude_unset=True, mode="json"))
        response = await self._http.put(f"{self._resolve_path()}/legacy", json=payload)
        return self.models.LegacyConfigGet.model_validate(response.json())

    async def delete_legacy_config(self) -> None:
        """Deletes legacy conversion settings."""
        await self._pacing_delay()
        await self._http.delete(f"{self._resolve_path()}/legacy")
