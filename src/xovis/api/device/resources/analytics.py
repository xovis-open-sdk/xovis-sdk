"""
Xovis SDK - Analytics Management Resource

Operates within the Control Plane.
Provides the implementation for managing complex analytics structures (logics,
modifiers, counters, and templates) on local edge sensors. Integrates atomic
transactions, capacity limits, and cascading deletes for autonomous agent workflows.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Optional, Union

from xovis.api.core.exceptions import MultipleResourcesFoundError, ResourceNotFoundError
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient
    from xovis.models.device import Counter, Logic, Modifier
    from xovis.models.device_auto.versions.v5_9_11 import (
        CounterCollection,
        ElementsLimits,
        LogicCollection,
        LogicTemplate,
        LogicTemplateCollection,
        ModifierCollection,
        Transaction,
    )


def _recursive_none_filter(data: Any) -> Any:
    """Recursively removes None values from dictionaries and lists."""
    if isinstance(data, dict):
        return {k: _recursive_none_filter(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [_recursive_none_filter(v) for v in data if v is not None]
    return data


class AnalyticsManager:
    """
    Manages analytics logics, modifiers, counters, and atomic transactions.

    This manager orchestrates the mathematical and spatial rules of the sensor.
    It supports querying hardware limits to prevent resource exhaustion and
    allows autonomous agents to execute complex configuration changes atomically.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the AnalyticsManager.

        Args:
            client (DeviceClient): The parent device client instance.
            target_id (Optional[str]): The multisensor target ID, if applicable.
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
            return f"/api/v5/multisensors/{self.target_id}/analysis"
        return "/api/v5/singlesensor/analysis"

    async def _resolve_logic_id(self, id_or_name: Union[int, str]) -> int:
        """
        Resolves a logic ID from either an ID or a human-readable name.

        Args:
            id_or_name (Union[int, str]): The integer ID or string name to resolve.

        Returns:
            int: The resolved numeric logic identifier.

        Raises:
            ResourceNotFoundError: If no logic matches the provided name.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        if isinstance(id_or_name, int) or (isinstance(id_or_name, str) and id_or_name.isdigit()):
            return int(id_or_name)

        multisensors = self._client.cache.multisensors
        if self.target_id:
            target_str = str(self.target_id)
            if target_str not in (multisensors._items if hasattr(multisensors, "_items") else multisensors):
                await self._client.multisensors.sync()
            context = multisensors[target_str]
        else:
            context = self._client.cache.singlesensor

        if context.logics is None or not any(l.name == id_or_name for l in context.logics):
            await self.get_all_logics()

        matches = [l for l in context.logics if l.name == id_or_name]
        if not matches:
            raise ResourceNotFoundError(f"No logic found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} logics named '{id_or_name}'.")
        return int(matches[0].id)

    async def _resolve_modifier_id(self, id_or_name: Union[int, str]) -> int:
        """
        Resolves a modifier ID from either an ID or a human-readable name.

        Args:
            id_or_name (Union[int, str]): The integer ID or string name to resolve.

        Returns:
            int: The resolved numeric modifier identifier.

        Raises:
            ResourceNotFoundError: If no modifier matches the provided name.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        if isinstance(id_or_name, int) or (isinstance(id_or_name, str) and id_or_name.isdigit()):
            return int(id_or_name)

        multisensors = self._client.cache.multisensors
        if self.target_id:
            target_str = str(self.target_id)
            if target_str not in (multisensors._items if hasattr(multisensors, "_items") else multisensors):
                await self._client.multisensors.sync()
            context = multisensors[target_str]
        else:
            context = self._client.cache.singlesensor

        if context.modifiers is None or not any(m.name == id_or_name for m in context.modifiers):
            await self.get_all_modifiers()

        matches = [m for m in context.modifiers if m.name == id_or_name]
        if not matches:
            raise ResourceNotFoundError(f"No modifier found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} modifiers named '{id_or_name}'.")
        return int(matches[0].id)

    async def _resolve_counter_id(self, id_or_name: Union[int, str]) -> int:
        """
        Resolves a counter ID from either an ID or a human-readable name.

        Args:
            id_or_name (Union[int, str]): The integer ID or string name to resolve.

        Returns:
            int: The resolved numeric counter identifier.

        Raises:
            ResourceNotFoundError: If no counter matches the provided name.
            MultipleResourcesFoundError: If the name is ambiguous.
        """
        if isinstance(id_or_name, int) or (isinstance(id_or_name, str) and id_or_name.isdigit()):
            return int(id_or_name)

        multisensors = self._client.cache.multisensors
        if self.target_id:
            target_str = str(self.target_id)
            if target_str not in (multisensors._items if hasattr(multisensors, "_items") else multisensors):
                await self._client.multisensors.sync()
            context = multisensors[target_str]
        else:
            context = self._client.cache.singlesensor

        if context.counters is None or not any(c.name == id_or_name for c in context.counters):
            await self.get_all_counters()

        matches = [c for c in context.counters if c.name == id_or_name]
        if not matches:
            raise ResourceNotFoundError(f"No counter found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} counters named '{id_or_name}'.")
        return int(matches[0].id)

    async def _pacing_delay(self) -> None:
        """
        Implements intra-mutation pacing to prevent sensor configuration OOM or service crashes.
        Mandatory for FW 5.9.2+ where rapid REST mutations can lead to hardware reboots.
        """
        await asyncio.sleep(2.0)

    # --- ATOMIC TRANSACTIONS ---
    async def execute_transaction(self, transaction: "Transaction", id_mode: str = "SERVER") -> "Transaction":
        """
        Executes a bundle of requests as a single atomic transaction.

        Args:
            transaction (Transaction): The transaction model containing a list
                of configuration mutations to execute atomically.
            id_mode (str): ID assignment strategy ("SERVER" or "CLIENT").

        Returns:
            Transaction: The executed transaction with updated IDs and statuses.
        """
        await self._pacing_delay()
        params = {"id_mode": id_mode}
        response = await self._http.post(f"{self._resolve_path()}/transaction", params=params, json=transaction)
        return self.models.Transaction.model_validate(response.json())

    # --- LOGICS ---
    async def get_logic_limits(self) -> "ElementsLimits":
        """
        Retrieves the maximum allowed number of logics for the device.
        """
        response = await self._http.get(f"{self._resolve_path()}/logics/limits")
        return self.models.ElementsLimits.model_validate(response.json())

    async def get_all_logics(self) -> "LogicCollection":
        """
        Retrieves all analytics logics from the sensor.

        Returns:
            LogicCollection: The collection of all configured analytics logics.
        """
        response = await self._http.get(f"{self._resolve_path()}/logics")
        collection = self.models.LogicCollection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        context.logics = collection.logics

        return collection

    async def get_logic(self, id_or_name: Union[int, str]) -> "Logic":
        """
        Retrieves a specific analytics logic.

        Args:
            id_or_name (Union[int, str]): The ID or name of the logic to retrieve.

        Returns:
            Logic: The retrieved analytics logic model.
        """
        logic_id = await self._resolve_logic_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/logics/{logic_id}")
        return self.models.Logic.model_validate(response.json())

    async def create_logic(self, logic: "Logic", id_mode: str = "SERVER") -> "Logic":
        """
        Creates a new analytics logic.

        Args:
            logic (Logic): The logic model to create.
            id_mode (str): ID assignment strategy ("SERVER" or "CLIENT").

        Returns:
            Logic: The created analytics logic with its assigned ID.
        """
        await self._pacing_delay()
        params = {"id_mode": id_mode}
        response = await self._http.post(f"{self._resolve_path()}/logics", params=params, json=logic)
        return self.models.Logic.model_validate(response.json())

    async def update_logic(self, id_or_name: Union[int, str], logic: "Logic") -> "Logic":
        """
        Updates an existing analytics logic.

        Args:
            id_or_name (Union[int, str]): The ID or name of the logic to update.
            logic (Logic): The updated logic model.

        Returns:
            Logic: The updated analytics logic.
        """
        await self._pacing_delay()
        logic_id = await self._resolve_logic_id(id_or_name)
        response = await self._http.put(f"{self._resolve_path()}/logics/{logic_id}", json=logic)
        return self.models.Logic.model_validate(response.json())

    async def delete_logic(self, id_or_name: Union[int, str], force: bool = False) -> None:
        """
        Deletes an analytics logic.

        Args:
            id_or_name (Union[int, str]): The ID or name of the logic to delete.
            force (bool): If True, forces deletion even if dependencies exist.
        """
        await self._pacing_delay()
        logic_id = await self._resolve_logic_id(id_or_name)
        params = {"force": "true" if force else "false"}
        await self._http.delete(f"{self._resolve_path()}/logics/{logic_id}", params=params)

    async def delete_all_logics(self, force: bool = False) -> None:
        """Deletes all analytics logics and optionally cascades dependencies."""
        await self._pacing_delay()
        params = {"force": "true" if force else "false"}
        await self._http.delete(f"{self._resolve_path()}/logics", params=params)

    async def reset_logic_counters(self, id_or_name: Union[int, str]) -> None:
        """
        Resets the relative/live values of all counters associated with this logic to zero.
        Does not affect the persisted historical database.
        """
        logic_id = await self._resolve_logic_id(id_or_name)
        await self._http.post(f"{self._resolve_path()}/logics/{logic_id}/reset")

    # --- LOGIC TEMPLATES ---
    async def get_all_logic_templates(self) -> "LogicTemplateCollection":
        """
        Retrieves all pre-configured logic templates.

        Returns:
            LogicTemplateCollection: The collection of available logic templates.
        """
        response = await self._http.get(f"{self._resolve_path()}/logics/templates")
        return self.models.LogicTemplateCollection.model_validate(response.json())

    async def create_logic_template(self, template: "LogicTemplate", id_mode: str = "SERVER") -> "LogicTemplate":
        """
        Instantiates a new logic template.

        Args:
            template (LogicTemplate): The template model to instantiate.
            id_mode (str): ID assignment strategy.

        Returns:
            LogicTemplate: The created logic template instance.
        """
        await self._pacing_delay()
        params = {"id_mode": id_mode}
        response = await self._http.post(f"{self._resolve_path()}/logics/templates", params=params, json=template)
        return self.models.LogicTemplate.model_validate(response.json())

    async def delete_logic_template(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes a specific logic template.

        Args:
            id_or_name (Union[int, str]): The ID or name of the template to delete.
        """
        await self._pacing_delay()
        template_id = await self._resolve_logic_id(id_or_name)
        await self._http.delete(f"{self._resolve_path()}/logics/templates/{template_id}")

    # --- MODIFIERS ---
    async def get_modifier_limits(self) -> "ElementsLimits":
        """Retrieves the maximum allowed number of modifiers for the device."""
        response = await self._http.get(f"{self._resolve_path()}/modifiers/limits")
        return self.models.ElementsLimits.model_validate(response.json())

    async def get_all_modifiers(self, logic_id: Optional[int] = None, counter_id: Optional[int] = None) -> "ModifierCollection":
        """
        Retrieves analytics modifiers, optionally filtered by parent relationships.

        Args:
            logic_id (Optional[int]): Restrict output to modifiers of a specific logic.
            counter_id (Optional[int]): Restrict output to modifiers manipulating a specific counter.
        """
        params = {}
        if logic_id is not None:
            params["logic_id"] = str(logic_id)
        if counter_id is not None:
            params["counter_id"] = str(counter_id)

        response = await self._http.get(f"{self._resolve_path()}/modifiers", params=params)
        collection = self.models.ModifierCollection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        context.modifiers = collection.modifiers

        return collection

    async def get_modifier(self, id_or_name: Union[int, str]) -> "Modifier":
        """
        Retrieves a specific analytics modifier.

        Args:
            id_or_name (Union[int, str]): The ID or name of the modifier to retrieve.

        Returns:
            Modifier: The retrieved analytics modifier model.
        """
        modifier_id = await self._resolve_modifier_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/modifiers/{modifier_id}")
        return self.models.Modifier.model_validate(response.json())

    async def create_modifier(self, modifier: "Modifier", id_mode: str = "SERVER") -> "Modifier":
        """
        Creates a new analytics modifier.

        Args:
            modifier (Modifier): The modifier model to create.
            id_mode (str): ID assignment strategy.

        Returns:
            Modifier: The created analytics modifier.
        """
        await self._pacing_delay()
        params = {"id_mode": id_mode}
        response = await self._http.post(f"{self._resolve_path()}/modifiers", params=params, json=modifier)
        return self.models.Modifier.model_validate(response.json())

    async def update_modifier(self, id_or_name: Union[int, str], modifier: "Modifier") -> "Modifier":
        """
        Updates an existing analytics modifier.

        Args:
            id_or_name (Union[int, str]): The ID or name of the modifier to update.
            modifier (Modifier): The updated modifier model.

        Returns:
            Modifier: The updated analytics modifier.
        """
        await self._pacing_delay()
        modifier_id = await self._resolve_modifier_id(id_or_name)
        response = await self._http.put(f"{self._resolve_path()}/modifiers/{modifier_id}", json=modifier)
        return self.models.Modifier.model_validate(response.json())

    async def delete_modifier(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes an analytics modifier.

        Args:
            id_or_name (Union[int, str]): The ID or name of the modifier to delete.
        """
        await self._pacing_delay()
        modifier_id = await self._resolve_modifier_id(id_or_name)
        await self._http.delete(f"{self._resolve_path()}/modifiers/{modifier_id}")

    async def delete_all_modifiers(self) -> None:
        """
        Deletes all analytics modifiers.
        """
        await self._pacing_delay()
        await self._http.delete(f"{self._resolve_path()}/modifiers")

    # --- COUNTERS ---
    async def get_counter_limits(self) -> "ElementsLimits":
        """Retrieves the maximum allowed number of counters for the device."""
        response = await self._http.get(f"{self._resolve_path()}/counters/limits")
        return self.models.ElementsLimits.model_validate(response.json())

    async def get_all_counters(self, logic_id: Optional[int] = None) -> "CounterCollection":
        """
        Retrieves analytics counters, optionally restricted to a specific logic.
        """
        params = {}
        if logic_id is not None:
            params["logic_id"] = str(logic_id)

        response = await self._http.get(f"{self._resolve_path()}/counters", params=params)
        collection = self.models.CounterCollection.model_validate(response.json())

        # Update cache
        multisensors = self._client.cache.multisensors
        context = (
            multisensors[str(self.target_id)]
            if self.target_id and str(self.target_id) in (multisensors._items if hasattr(multisensors, "_items") else multisensors)
            else self._client.cache.singlesensor
        )
        context.counters = collection.counters

        return collection

    async def get_counter(self, id_or_name: Union[int, str]) -> "Counter":
        """
        Retrieves a specific analytics counter.

        Args:
            id_or_name (Union[int, str]): The ID or name of the counter to retrieve.

        Returns:
            Counter: The retrieved analytics counter model.
        """
        counter_id = await self._resolve_counter_id(id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/counters/{counter_id}")
        return self.models.Counter.model_validate(response.json())

    async def create_counter(self, counter: "Counter", id_mode: str = "SERVER") -> "Counter":
        """
        Creates a new analytics counter.

        Args:
            counter (Counter): The counter model to create.
            id_mode (str): ID assignment strategy.

        Returns:
            Counter: The created analytics counter.
        """
        await self._pacing_delay()
        params = {"id_mode": id_mode}
        response = await self._http.post(f"{self._resolve_path()}/counters", params=params, json=counter)
        return self.models.Counter.model_validate(response.json())

    async def update_counter(self, id_or_name: Union[int, str], counter: "Counter") -> "Counter":
        """
        Updates an existing analytics counter.

        Args:
            id_or_name (Union[int, str]): The ID or name of the counter to update.
            counter (Counter): The updated counter model.

        Returns:
            Counter: The updated analytics counter.
        """
        await self._pacing_delay()
        counter_id = await self._resolve_counter_id(id_or_name)
        response = await self._http.put(f"{self._resolve_path()}/counters/{counter_id}", json=counter)
        return self.models.Counter.model_validate(response.json())

    async def delete_counter(self, id_or_name: Union[int, str], force: bool = False) -> None:
        """
        Deletes an analytics counter.
        """
        await self._pacing_delay()
        counter_id = await self._resolve_counter_id(id_or_name)
        params = {"force": "true" if force else "false"}
        await self._http.delete(f"{self._resolve_path()}/counters/{counter_id}", params=params)

    async def delete_all_counters(self, force: bool = False) -> None:
        """Deletes all analytics counters and optionally cascades dependencies."""
        await self._pacing_delay()
        params = {"force": "true" if force else "false"}
        await self._http.delete(f"{self._resolve_path()}/counters", params=params)

    async def reset_counter(self, id_or_name: Union[int, str]) -> None:
        """
        Resets the relative/live value of a specific counter to zero.
        """
        counter_id = await self._resolve_counter_id(id_or_name)
        await self._http.post(f"{self._resolve_path()}/counters/{counter_id}/reset")

    async def reset_all_counters(self) -> None:
        """
        Resets the relative/live values of all counters to zero.
        """
        await self._http.post(f"{self._resolve_path()}/counters/reset")
