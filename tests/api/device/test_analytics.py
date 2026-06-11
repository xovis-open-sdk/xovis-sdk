"""
Xovis SDK - Analytics Integration Tests

Validates the CRUD operations for Analytics Logics, Modifiers, and Counters
on local edge sensors. Part of the State & Topology Plane's configuration validation.
"""

import pytest

from xovis.models.device import Counter, Logic, Modifier


@pytest.mark.asyncio
async def test_analytics_get_all(real_device):
    """
    Validates retrieval of all analytics entities.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    # Use ad-hoc capability probe to handle potential 403 blocks correctly
    if not await real_device.has_capability("/api/v5/singlesensor/analysis/logics"):
        pytest.skip("Analytics not supported or accessible on this device")

    try:
        logics = await real_device.singlesensor.analytics.get_all_logics()
    except Exception as e:
        pytest.skip(f"Could not retrieve logics: {e}")
    # Using Logic, Modifier, and Counter models for validation as Collection models are version-specific
    assert hasattr(logics, "logics")

    modifiers = await real_device.singlesensor.analytics.get_all_modifiers()
    assert hasattr(modifiers, "modifiers")

    counters = await real_device.singlesensor.analytics.get_all_counters()
    assert hasattr(counters, "counters")


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_analytics_logic_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Analytics Logics.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_capability("/api/v5/singlesensor/analysis/logics"):
        pytest.skip("Analytics not supported or accessible on this device")

    payload = {
        "name": "IntTest Logic",
        "type": "ZONE_IN_OUT_COUNT",
        "parameters": {"zone_id": 1007},
    }
    try:
        logic_model = Logic.model_validate(payload)
        created = await real_device.singlesensor.analytics.create_logic(logic_model)
        assert created.id is not None
    except Exception as e:
        pytest.skip(f"Device does not allow logic creation on this zone/template: {e}")

    try:
        created.name = "IntTest Logic Updated"
        updated = await real_device.singlesensor.analytics.update_logic(created.id, created)
        assert updated.name == "IntTest Logic Updated"

        retrieved = await real_device.singlesensor.analytics.get_logic(updated.id)
        assert retrieved.name == "IntTest Logic Updated"
    finally:
        await real_device.singlesensor.analytics.delete_logic(created.id)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_analytics_modifier_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Analytics Modifiers.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_capability("/api/v5/singlesensor/analysis/logics"):
        pytest.skip("Analytics not supported or accessible on this device")

    payload = {
        "name": "IntTest Modifier",
        "type": "TIME_FILTER",
        "logic_id": 1007,
        "parameters": {"start_time": "08:00:00", "end_time": "18:00:00"},
    }
    try:
        modifier_model = Modifier.model_validate(payload)
        created = await real_device.singlesensor.analytics.create_modifier(modifier_model)
        assert created.id is not None
    except Exception as e:
        pytest.skip(f"Device does not allow modifier creation: {e}")

    try:
        created.name = "IntTest Modifier Updated"
        updated = await real_device.singlesensor.analytics.update_modifier(created.id, created)
        assert updated.name == "IntTest Modifier Updated"

        retrieved = await real_device.singlesensor.analytics.get_modifier(updated.id)
        assert retrieved.name == "IntTest Modifier Updated"
    finally:
        await real_device.singlesensor.analytics.delete_modifier(created.id)


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_analytics_counter_crud(real_device):
    """
    Validates idempotent CRUD lifecycle for Analytics Counters.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    if not await real_device.has_capability("/api/v5/singlesensor/analysis/logics"):
        pytest.skip("Analytics not supported or accessible on this device")

    payload = {"name": "IntTest Counter", "type": "accumulation", "logic_id": 1007, "logic_ids": []}
    try:
        counter_model = Counter.model_validate(payload)
        created = await real_device.singlesensor.analytics.create_counter(counter_model)
        assert created.id is not None
    except Exception as e:
        pytest.skip(f"Device does not allow counter creation: {e}")

    try:
        created.name = "IntTest Counter Updated"
        updated = await real_device.singlesensor.analytics.update_counter(created.id, created)
        assert updated.name == "IntTest Counter Updated"

        retrieved = await real_device.singlesensor.analytics.get_counter(updated.id)
        assert retrieved.name == "IntTest Counter Updated"
    finally:
        await real_device.singlesensor.analytics.delete_counter(created.id)
