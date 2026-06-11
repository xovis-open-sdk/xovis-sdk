"""
Xovis SDK - Scene Management Resource

Operates within the Control Plane.
Provides the implementation for managing spatial constraints on local edge sensors,
including scene geometries (lines/zones), occlusion masks, layers, objects,
and attention areas. Integrates capacity limit queries to prevent autonomous
agents from exceeding edge hardware vertex constraints.
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from xovis.api.core.exceptions import MultipleResourcesFoundError, ResourceNotFoundError
from xovis.models.device_auto import stable_models

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient
    from xovis.models.device_auto.versions.v5_9_11 import (
        AllSceneMasks,
        Attention,
        Attentions,
        AttentionsLimits,
        Layer,
        Layers,
        LayersLimits,
        SceneGeometries,
        SceneGeometriesLimits,
        SceneGeometry,
        SceneMask,
        SceneMasksLimits,
        SceneObject,
        SceneObjects,
        SceneObjectsLimits,
    )


def _recursive_none_filter(data: Any) -> Any:
    """Recursively removes None values from dictionaries and lists."""
    if isinstance(data, dict):
        return {k: _recursive_none_filter(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [_recursive_none_filter(v) for v in data if v is not None]
    return data


class SceneManager:
    """
    Manages the physical and optical spatial context of a Xovis device.

    Orchestrates the creation and modification of Geometries, Masks, Layers,
    Scene Objects, and Attentions. Exposes hardware vertex and element limits
    to ensure autonomous generation agents (Module C) remain within safe bounds.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the SceneManager.

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
            return f"/api/v5/multisensors/{self.target_id}/scene"
        return "/api/v5/singlesensor/scene"

    async def _resolve_resource_id(self, resource_type: str, id_or_name: Union[int, str]) -> int:
        """
        Generic resolver for translating human-readable names to integer IDs
        by inspecting the persistent HostStateBucket cache.

        Args:
            resource_type (str): The collection name in the cache (e.g., 'zones', 'masks').
            id_or_name (Union[int, str]): The ID or name to resolve.

        Returns:
            int: The resolved exact integer ID.

        Raises:
            ResourceNotFoundError: If the name is missing from the cache.
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

        # Geometries are split into lines and zones in the cache bucket
        if resource_type == "geometries":
            items = list(getattr(context, "zones", []) or []) + list(getattr(context, "lines", []) or [])
        else:
            items = list(getattr(context, resource_type, []) or [])

        # Proactive sync if name is not found
        if not any(getattr(item, "name", None) == id_or_name for item in items):
            if resource_type == "geometries":
                await self.get_all_geometries()
            elif resource_type == "masks":
                await self.get_all_masks()
            elif resource_type == "layers":
                await self.get_all_layers()
            elif resource_type == "scene_objects":
                await self.get_all_objects()
            elif resource_type == "attentions":
                await self.get_all_attentions()

            # Re-fetch items after sync
            if resource_type == "geometries":
                items = list(getattr(context, "zones", []) or []) + list(getattr(context, "lines", []) or [])
            else:
                items = list(getattr(context, resource_type, []) or [])

        matches = [item for item in items if getattr(item, "name", None) == id_or_name]

        if not matches:
            raise ResourceNotFoundError(f"No {resource_type} found with name '{id_or_name}'.")
        if len(matches) > 1:
            raise MultipleResourcesFoundError(f"Found {len(matches)} {resource_type} named '{id_or_name}'. Use integer ID.")
        return int(matches[0].id)

    # --- GEOMETRIES ---
    async def get_geometry_limits(self) -> "SceneGeometriesLimits":
        """Retrieves the maximum allowed geometries and total vertices for the device."""
        response = await self._http.get(f"{self._resolve_path()}/geometries/limits")
        return self.models.SceneGeometriesLimits.model_validate(response.json())

    async def get_all_geometries(self, layer_id: Optional[int] = None) -> "SceneGeometries":
        """
        Retrieves all active lines and zones, optionally filtered by layer.

        Args:
            layer_id (Optional[int]): If provided, only returns geometries
                associated with this specific layer ID.

        Returns:
            SceneGeometries: A collection of all matching lines and zones.
        """
        params = {"layer_id": str(layer_id)} if layer_id is not None else {}
        response = await self._http.get(f"{self._resolve_path()}/geometries", params=params)
        return self.models.SceneGeometries.model_validate(response.json())

    async def get_geometry(self, id_or_name: Union[int, str]) -> "SceneGeometry":
        """
        Retrieves a specific scene geometry configuration.

        Args:
            id_or_name (Union[int, str]): The ID or logical name of the geometry.

        Returns:
            SceneGeometry: The validated scene geometry configuration.
        """
        geom_id = await self._resolve_resource_id("geometries", id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/geometries/{geom_id}")
        return self.models.SceneGeometry.model_validate(response.json())

    async def create_geometry(self, geometry: "SceneGeometry", id_mode: str = "SERVER") -> "SceneGeometry":
        """Provisions a new physical tracking geometry (line or polygon)."""
        params = {"id_mode": id_mode}
        payload = _recursive_none_filter(geometry.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.post(f"{self._resolve_path()}/geometries", params=params, json=payload)
        return self.models.SceneGeometry.model_validate(response.json())

    async def update_geometry(self, id_or_name: Union[int, str], geometry: "SceneGeometry") -> "SceneGeometry":
        """
        Replaces an existing scene geometry.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target geometry.
            geometry (SceneGeometry): The full updated geometry configuration.

        Returns:
            SceneGeometry: The successfully updated geometry.
        """
        geom_id = await self._resolve_resource_id("geometries", id_or_name)
        payload = _recursive_none_filter(geometry.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.put(f"{self._resolve_path()}/geometries/{geom_id}", json=payload)
        return self.models.SceneGeometry.model_validate(response.json())

    async def delete_geometry(self, id_or_name: Union[int, str]) -> None:
        """
        Removes a specific scene geometry.

        Args:
            id_or_name (Union[int, str]): The ID or name of the geometry to delete.
        """
        geom_id = await self._resolve_resource_id("geometries", id_or_name)
        await self._http.delete(f"{self._resolve_path()}/geometries/{geom_id}")

    async def delete_all_geometries(self) -> None:
        """Destructively removes all scene geometries."""
        await self._http.delete(f"{self._resolve_path()}/geometries")

    # --- MASKS ---
    async def get_mask_limits(self) -> "SceneMasksLimits":
        """Retrieves the maximum allowed masks and vertices for the device."""
        response = await self._http.get(f"{self._resolve_path()}/masks/limits")
        return self.models.SceneMasksLimits.model_validate(response.json())

    async def get_all_masks(self) -> "AllSceneMasks":
        """
        Retrieves all exclusion and illumination masks.

        Returns:
            AllSceneMasks: A collection of all configured masks.
        """
        response = await self._http.get(f"{self._resolve_path()}/masks")
        return self.models.AllSceneMasks.model_validate(response.json())

    async def get_mask(self, id_or_name: Union[int, str]) -> "SceneMask":
        """
        Retrieves a specific exclusion mask.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target mask.

        Returns:
            SceneMask: The validated mask configuration.
        """
        mask_id = await self._resolve_resource_id("masks", id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/masks/{mask_id}")
        return self.models.SceneMask.model_validate(response.json())

    async def create_mask(self, mask: "SceneMask", id_mode: str = "SERVER") -> "SceneMask":
        """Creates a new exclusion or illumination mask."""
        params = {"id_mode": id_mode}
        payload = _recursive_none_filter(mask.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.post(f"{self._resolve_path()}/masks", params=params, json=payload)
        return self.models.SceneMask.model_validate(response.json())

    async def update_mask(self, id_or_name: Union[int, str], mask: "SceneMask") -> "SceneMask":
        """
        Updates an existing mask.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target mask.
            mask (SceneMask): The updated mask configuration.

        Returns:
            SceneMask: The successfully updated mask.
        """
        mask_id = await self._resolve_resource_id("masks", id_or_name)
        payload = _recursive_none_filter(mask.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.put(f"{self._resolve_path()}/masks/{mask_id}", json=payload)
        return self.models.SceneMask.model_validate(response.json())

    async def delete_mask(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes a specific exclusion mask.

        Args:
            id_or_name (Union[int, str]): The ID or name of the mask to delete.
        """
        mask_id = await self._resolve_resource_id("masks", id_or_name)
        await self._http.delete(f"{self._resolve_path()}/masks/{mask_id}")

    async def delete_all_masks(self) -> None:
        """Destructively removes all scene masks."""
        await self._http.delete(f"{self._resolve_path()}/masks")

    # --- LAYERS ---
    async def get_layer_limits(self) -> "LayersLimits":
        """Retrieves the maximum allowed layers and constraints for the device."""
        response = await self._http.get(f"{self._resolve_path()}/layers/limits")
        return self.models.LayersLimits.model_validate(response.json())

    async def get_all_layers(self) -> "Layers":
        """
        Retrieves all scene layers (virtual sub-contexts).

        Returns:
            Layers: A collection of all defined layers.
        """
        response = await self._http.get(f"{self._resolve_path()}/layers")
        return self.models.Layers.model_validate(response.json())

    async def get_layer(self, id_or_name: Union[int, str]) -> "Layer":
        """
        Retrieves a specific scene layer.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target layer.

        Returns:
            Layer: The validated layer configuration.
        """
        layer_id = await self._resolve_resource_id("layers", id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/layers/{layer_id}")
        return self.models.Layer.model_validate(response.json())

    async def create_layer(self, layer: "Layer", id_mode: str = "SERVER") -> "Layer":
        """Provisions a new logical scene layer."""
        params = {"id_mode": id_mode}
        payload = _recursive_none_filter(layer.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.post(f"{self._resolve_path()}/layers", params=params, json=payload)
        return self.models.Layer.model_validate(response.json())

    async def update_layer(self, id_or_name: Union[int, str], layer: "Layer") -> "Layer":
        """
        Updates an existing scene layer.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target layer.
            layer (Layer): The updated layer configuration.

        Returns:
            Layer: The successfully updated layer.
        """
        layer_id = await self._resolve_resource_id("layers", id_or_name)
        payload = _recursive_none_filter(layer.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.put(f"{self._resolve_path()}/layers/{layer_id}", json=payload)
        return self.models.Layer.model_validate(response.json())

    async def delete_layer(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes a specific scene layer.

        Args:
            id_or_name (Union[int, str]): The ID or name of the layer to delete.
        """
        layer_id = await self._resolve_resource_id("layers", id_or_name)
        await self._http.delete(f"{self._resolve_path()}/layers/{layer_id}")

    async def delete_all_layers(self) -> None:
        """Destructively removes all scene layers."""
        await self._http.delete(f"{self._resolve_path()}/layers")

    # --- SCENE OBJECTS ---
    async def get_object_limits(self) -> "SceneObjectsLimits":
        """Retrieves the maximum allowed scene objects and vertices for the device."""
        response = await self._http.get(f"{self._resolve_path()}/objects/limits")
        return self.models.SceneObjectsLimits.model_validate(response.json())

    async def get_all_objects(self) -> "SceneObjects":
        """
        Retrieves all physical Scene Objects (e.g., tables, barriers).

        Returns:
            SceneObjects: A collection of all configured scene objects.
        """
        response = await self._http.get(f"{self._resolve_path()}/objects")
        return self.models.SceneObjects.model_validate(response.json())

    async def get_object(self, id_or_name: Union[int, str]) -> "SceneObject":
        """
        Retrieves a specific Scene Object.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target object.

        Returns:
            SceneObject: The validated scene object configuration.
        """
        obj_id = await self._resolve_resource_id("scene_objects", id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/objects/{obj_id}")
        return self.models.SceneObject.model_validate(response.json())

    async def create_object(self, scene_object: "SceneObject", id_mode: str = "SERVER") -> "SceneObject":
        """Creates a new Scene Object for physical environment tracking."""
        params = {"id_mode": id_mode}
        payload = _recursive_none_filter(scene_object.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.post(f"{self._resolve_path()}/objects", params=params, json=payload)
        return self.models.SceneObject.model_validate(response.json())

    async def update_object(self, id_or_name: Union[int, str], scene_object: "SceneObject") -> "SceneObject":
        """
        Updates an existing Scene Object.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target object.
            scene_object (SceneObject): The updated object configuration.

        Returns:
            SceneObject: The successfully updated object.
        """
        obj_id = await self._resolve_resource_id("scene_objects", id_or_name)
        payload = _recursive_none_filter(scene_object.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.put(f"{self._resolve_path()}/objects/{obj_id}", json=payload)
        return self.models.SceneObject.model_validate(response.json())

    async def delete_object(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes a specific Scene Object.

        Args:
            id_or_name (Union[int, str]): The ID or name of the object to delete.
        """
        obj_id = await self._resolve_resource_id("scene_objects", id_or_name)
        await self._http.delete(f"{self._resolve_path()}/objects/{obj_id}")

    async def delete_all_objects(self) -> None:
        """Destructively removes all Scene Objects."""
        await self._http.delete(f"{self._resolve_path()}/objects")

    # --- ATTENTIONS ---
    async def get_attention_limits(self) -> "AttentionsLimits":
        """Retrieves the maximum allowed Attention areas for the device."""
        response = await self._http.get(f"{self._resolve_path()}/attentions/limits")
        return self.models.AttentionsLimits.model_validate(response.json())

    async def get_all_attentions(self, layer_id: Optional[int] = None) -> "Attentions":
        """
        Retrieves all configured Attention areas, optionally filtered by layer.

        Args:
            layer_id (Optional[int]): Filter by a specific layer ID.

        Returns:
            Attentions: A collection of matching attention area configurations.
        """
        params = {"layer_id": str(layer_id)} if layer_id is not None else {}
        response = await self._http.get(f"{self._resolve_path()}/attentions", params=params)
        return self.models.Attentions.model_validate(response.json())

    async def get_attention(self, id_or_name: Union[int, str]) -> "Attention":
        """
        Retrieves a specific Attention area.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target area.

        Returns:
            Attention: The validated attention area configuration.
        """
        attention_id = await self._resolve_resource_id("attentions", id_or_name)
        response = await self._http.get(f"{self._resolve_path()}/attentions/{attention_id}")
        return self.models.Attention.model_validate(response.json())

    async def create_attention(self, attention: "Attention", id_mode: str = "SERVER") -> "Attention":
        """Creates a new Attention area for measuring subject engagement."""
        params = {"id_mode": id_mode}
        payload = _recursive_none_filter(attention.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.post(f"{self._resolve_path()}/attentions", params=params, json=payload)
        return self.models.Attention.model_validate(response.json())

    async def update_attention(self, id_or_name: Union[int, str], attention: "Attention") -> "Attention":
        """
        Updates an existing Attention area.

        Args:
            id_or_name (Union[int, str]): The ID or name of the target area.
            attention (Attention): The updated attention area configuration.

        Returns:
            Attention: The successfully updated attention area.
        """
        attention_id = await self._resolve_resource_id("attentions", id_or_name)
        payload = _recursive_none_filter(attention.model_dump(mode="json", by_alias=True, exclude_unset=True))
        response = await self._http.put(f"{self._resolve_path()}/attentions/{attention_id}", json=payload)
        return self.models.Attention.model_validate(response.json())

    async def delete_attention(self, id_or_name: Union[int, str]) -> None:
        """
        Deletes a specific Attention area.

        Args:
            id_or_name (Union[int, str]): The ID or name of the area to delete.
        """
        attention_id = await self._resolve_resource_id("attentions", id_or_name)
        await self._http.delete(f"{self._resolve_path()}/attentions/{attention_id}")

    async def delete_all_attentions(self) -> None:
        """Destructively removes all configured Attention areas."""
        await self._http.delete(f"{self._resolve_path()}/attentions")
