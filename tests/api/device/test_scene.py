"""
Xovis SDK - Scene Management Integration Tests

Validates the CRUD operations for Scene Geometries, Masks, and Layers
on local edge sensors. Part of the State & Topology Plane's configuration validation.
"""

import pytest

from xovis.models.device_auto import Layer, SceneGeometries, SceneGeometry, SceneMask


@pytest.mark.asyncio
async def test_scene_get_all_geometries(real_device):
    """
    Validates retrieval of all scene geometries.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical scene geometries.")

    geometries = await real_device.singlesensor.scene.get_all_geometries()
    assert isinstance(geometries, SceneGeometries)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_scene_geometry_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Scene Geometries.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical scene geometries.")

    payload = {"name": "IntTest Line", "type": "LINE", "geometry": [[0.0, 0.0], [1.0, 1.0]]}
    geom_model = SceneGeometry.model_validate(payload)

    created = await real_device.singlesensor.scene.create_geometry(geom_model)
    assert isinstance(created, SceneGeometry)
    assert created.id is not None

    try:
        created.name = "IntTest Line Updated"
        updated = await real_device.singlesensor.scene.update_geometry(created.id, created)
        assert isinstance(updated, SceneGeometry)
        assert updated.name == "IntTest Line Updated"

        retrieved = await real_device.singlesensor.scene.get_geometry(updated.id)
        assert isinstance(retrieved, SceneGeometry)
        assert retrieved.name == "IntTest Line Updated"
    finally:
        await real_device.singlesensor.scene.delete_geometry(created.id)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_scene_mask_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Scene Masks.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical scene masks.")

    payload = {
        "name": "IntTest Mask",
        "type": "EXCLUSION",
        "geometry": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]],
    }
    mask_model = SceneMask.model_validate(payload)
    created = await real_device.singlesensor.scene.create_mask(mask_model)
    assert created.id is not None

    try:
        created.name = "IntTest Mask Updated"
        updated = await real_device.singlesensor.scene.update_mask(created.id, created)
        assert updated.name == "IntTest Mask Updated"

        retrieved = await real_device.singlesensor.scene.get_mask(updated.id)
        assert retrieved.name == "IntTest Mask Updated"
    finally:
        await real_device.singlesensor.scene.delete_mask(created.id)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_scene_layer_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Scene Layers.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if real_device.is_spider:
        pytest.skip("Spider NUC does not support physical scene layers.")

    payload = {"name": "IntTest Layer"}
    layer_model = Layer.model_validate(payload)
    created = await real_device.singlesensor.scene.create_layer(layer_model)
    assert created.id is not None

    try:
        created.name = "IntTest Layer Updated"
        updated = await real_device.singlesensor.scene.update_layer(created.id, created)
        assert updated.name == "IntTest Layer Updated"

        retrieved = await real_device.singlesensor.scene.get_layer(updated.id)
        assert retrieved.name == "IntTest Layer Updated"
    finally:
        await real_device.singlesensor.scene.delete_layer(created.id)
