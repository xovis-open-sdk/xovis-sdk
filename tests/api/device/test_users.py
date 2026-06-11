"""
Xovis SDK - User Management Integration Tests

Validates the user account configuration, activation states, and credential
management on local edge sensors. Part of the State & Topology Plane's
security validation layer.
"""

import pytest

from xovis.models.device_auto import UserActivation, UserDetail, UserDetails


@pytest.mark.asyncio
async def test_users_get_all(real_device):
    """
    Validates retrieval of all configured user accounts.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    users = await real_device.users.get_all()
    assert users.users is not None
    assert len(users.users) > 0


@pytest.mark.asyncio
async def test_users_get_current(real_device):
    """
    Validates retrieval of the currently authenticated user's details.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    current_user = await real_device.users.get_current()
    assert current_user.id is not None


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_users_activation_toggle(real_device):
    """
    Validates toggling the activation state of a user account.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    users = await real_device.users.get_all()
    target_user = next((u for u in users.users if u.id != "admin"), None)

    if target_user is None:
        pytest.skip("No non-admin user found to test activation toggle")

    original_state = target_user.active
    try:
        await real_device.users.update_activation(target_user.id, UserActivation(active=False))
        updated = await real_device.users.get_user(target_user.id)
        assert updated.active is False

    finally:
        await real_device.users.update_activation(target_user.id, UserActivation(active=original_state))
        restored = await real_device.users.get_user(target_user.id)
        assert restored.active == original_state


@pytest.mark.asyncio
@pytest.mark.destructive
async def test_users_password_toggle(real_device):
    """
    Validates resetting a user's password to defaults.

    Args:
        real_device (DeviceClient): The local device client fixture.
    """
    users = await real_device.users.get_all()
    target_user = next((u for u in users.users if u.id != "admin"), None)

    if target_user is None:
        pytest.skip("No non-admin user found to test password reset")

    try:
        await real_device.users.reset_password(target_user.id)
    finally:
        pass
