"""
Xovis SDK - Global Test Configuration and Fixtures

Defines session and function-scoped fixtures for interacting with real
hardware and the Xovis HUB Cloud. This module ensures proper authentication,
event loop isolation, and connection pool management across the test suite.
"""

import os
import socket

import pytest
import pytest_asyncio

from xovis.api.device.client import DeviceClient
from xovis.api.hub.client import HubClient


@pytest_asyncio.fixture(scope="function")
async def real_hub():
    """
    Session-scoped fixture providing an authenticated HubClient.

    Utilizes environment variables for Auth0 credentials. Session scoping is
    critical to prevent HTTP 429 Rate Limits from the Auth0 identity provider.

    Args:
        None

    Returns:
        HubClient: An authenticated orchestrator for the Xovis HUB Cloud.

    Raises:
        pytest.skip: If required HUB credentials are not found in the environment.
    """
    token = os.getenv("XOVIS_HUB_TOKEN")
    client_id = os.getenv("XOVIS_HUB_CLIENT_ID")
    client_secret = os.getenv("XOVIS_HUB_CLIENT_SECRET")

    if token:
        client = HubClient(token=token)
    elif client_id and client_secret:
        client = HubClient(client_id=client_id, client_secret=client_secret)
    else:
        pytest.skip("Xovis Hub API credentials not found. Skipping.")

    # Note: HubClient.__aenter__ triggers cache sync
    async with client as c:
        yield c


@pytest.fixture(scope="session")
def local_routing_ip() -> str:
    """
    Dynamically resolves the host machine's IP address routable to the sensor.

    This utility is essential for configuring the DataPush connection on the
    hardware, ensuring the sensor knows where to stream its telemetry.

    Returns:
        str: The local IP address used to reach the `XOVIS_DEVICE_IP`.
    """
    host = os.getenv("XOVIS_DEVICE_IP", os.getenv("XOVIS_TEST_HOST", "127.0.0.1"))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((host, 80))
        local_ip = s.getsockname()[0]
        return local_ip
    finally:
        s.close()


@pytest_asyncio.fixture(name="real_device")
async def real_device_fixture():
    """
    Function-scoped fixture providing a connected DeviceClient (mocked or real).
    """
    host = os.getenv("XOVIS_DEVICE_IP")
    user = os.getenv("XOVIS_DEVICE_USERNAME", "admin")
    password = os.getenv("XOVIS_DEVICE_PASSWORD", "pass")

    if not host:
        # CI/Mock Mode: No hardware host provided
        from unittest.mock import AsyncMock, MagicMock

        import httpx

        from xovis.api.device.client import SinglesensorContext
        from xovis.models.device import (
            DataPushAgent,
            DataPushAgentCollection,
            DataPushConnection,
            DataPushConnectionCollection,
            DataPushStatusCollection,
            DataPushTestResponse,
            DataPushTriggerInfo,
            DataPushTriggerStatus,
            HistoryLogics,
            HTTPConfig,
            SystemInfo,
        )
        from xovis.models.device_auto import (
            DeviceInfo,
            DeviceState1,
            Hostname,
            ItxptConfig,
            ItxptServicesState,
            ItxptState,
            NetworkIpv4Settings,
            NetworkIpv6Settings,
            NetworkState,
            TimeSettings,
            TimeState,
            Timezones,
            UserDetail,
            UserDetails,
            stable_models,
        )

        mock_client = MagicMock(name="real_device")
        mock_client.host = "127.0.0.1"
        mock_client._http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client._http_client.base_url = httpx.URL("http://127.0.0.1")

        # Setup common async context manager behavior
        # Ensure it works correctly when used as 'async with real_device as client'
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Capability mocking: Ensure it returns True for analytics if requested
        async def mock_has_capability(path: str) -> bool:
            if "analysis" in path or "analytics" in path:
                return True
            return False

        mock_client.has_capability = AsyncMock(side_effect=mock_has_capability)

        async def mock_has_analytics():
            return True

        mock_client.has_analytics = AsyncMock(side_effect=mock_has_analytics)

        async def mock_has_wifi():
            return True

        mock_client.has_wifi = AsyncMock(side_effect=mock_has_wifi)

        async def mock_has_itxpt_func():
            return True

        mock_client.has_itxpt = AsyncMock(side_effect=mock_has_itxpt_func)

        async def mock_has_object_detection():
            return True

        mock_client.has_object_detection = AsyncMock(side_effect=mock_has_object_detection)

        async def mock_has_pram_detection():
            return True

        mock_client.has_pram_detection = AsyncMock(side_effect=mock_has_pram_detection)

        async def mock_has_wheelchair_detection():
            return True

        mock_client.has_wheelchair_detection = AsyncMock(side_effect=mock_has_wheelchair_detection)

        async def mock_has_bicycle_detection():
            return True

        mock_client.has_bicycle_detection = AsyncMock(side_effect=mock_has_bicycle_detection)

        async def mock_has_people_attributes():
            return True

        mock_client.has_people_attributes = AsyncMock(side_effect=mock_has_people_attributes)
        mock_client.models = stable_models

        # Mock multisensors sync and active_contexts
        mock_client.multisensors = MagicMock(name="multisensors")
        mock_client.multisensors.sync = AsyncMock()
        mock_client.multisensors.__bool__ = MagicMock(return_value=True)

        # Mock active_contexts to support async iteration
        mock_context = MagicMock(spec=SinglesensorContext, name="singlesensor")
        mock_context.name = "singlesensor"
        mock_context.singlesensor = mock_context
        mock_active_contexts = [mock_context]

        class AsyncIter:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        # Attach to mock_client (which is the real_device fixture's value)
        mock_client.active_contexts = mock_active_contexts
        # We need to make mock_client itself an async iterator because tests do 'await real_device.__anext__()'
        # and also 'for context in device.active_contexts' (if active_contexts is an async iterator?)
        # Actually, test_cp_datapush_crud.py:50 does 'device = await real_device.__anext__()'
        # where real_device IS the mock_client.

        # To support 'await mock_client.__anext__()', we must use an AsyncMock but it must be allowed.
        # MagicMock with spec might block setting magic methods if they are not in the spec.
        # But DeviceClient doesn't necessarily have __anext__ in its spec if it's not defined.

        # We'll use a simpler approach for the mock_client itself.
        mock_client.__aiter__ = MagicMock(return_value=AsyncIter(mock_active_contexts))
        mock_client.__anext__ = AsyncMock(return_value=mock_client)

        # Datapush manager mocking
        mock_datapush = MagicMock(name="datapush")
        mock_datapush.get_all_agents = AsyncMock(return_value=DataPushAgentCollection.model_construct(agents=[]))
        mock_datapush.get_all_connections = AsyncMock(return_value=DataPushConnectionCollection.model_construct(connections=[]))
        mock_datapush.create_agent = AsyncMock(side_effect=lambda agent, **kwargs: agent)
        mock_datapush.create_connection = AsyncMock(
            side_effect=lambda conn, **kwargs: DataPushConnection.model_validate(
                {
                    "id": conn.id if conn.id is not None else 9999,
                    "name": conn.name,
                    "protocol": conn.protocol,
                    "config": conn.config.model_dump(by_alias=True),
                }
            )
        )
        mock_datapush.delete_agent = AsyncMock()
        mock_datapush.delete_connection = AsyncMock()
        mock_datapush.delete_all_agents = AsyncMock()
        mock_datapush.delete_all_connections = AsyncMock()
        mock_datapush.get_agent_trigger_status = AsyncMock(return_value=DataPushTriggerInfo.model_construct(status=DataPushTriggerStatus.IDLE))
        mock_datapush.abort_agent_trigger = AsyncMock()
        mock_datapush.get_agent = AsyncMock(
            side_effect=lambda id_or_name: DataPushAgent.model_validate(
                {
                    "id": int(id_or_name) if str(id_or_name).isdigit() else 9999,
                    "name": str(id_or_name),
                    "type": "LOGICS",
                    "connection": 9999,
                    "enabled": True,
                    "config": {
                        "scheduler": {"type": "INTERVAL", "interval": "ONE_MINUTE"},
                        "data": {"format": {"type": "JSON"}, "resolution": "ONE_MINUTE"},
                    },
                }
            )
        )

        async def mock_patch_agent(id_or_name, updates):
            # For now, just ignore it in mock mode.
            pass

        mock_datapush.patch_agent = AsyncMock(side_effect=mock_patch_agent)
        mock_datapush.get_connection = AsyncMock(
            side_effect=lambda id_or_name: DataPushConnection.model_construct(
                id=id_or_name, config=HTTPConfig.model_construct(uri="http://127.0.0.1")
            )
        )
        mock_datapush.patch_connection = AsyncMock()
        mock_datapush.trigger_agent_push = AsyncMock(return_value=DataPushTriggerInfo.model_construct(status=DataPushTriggerStatus.IDLE))
        mock_datapush.test_connection = AsyncMock(return_value=DataPushTestResponse.model_construct(success=False, status="SERVER_ERROR"))

        # Mock status collection with valid nested structures
        status_collection = DataPushStatusCollection.model_construct(status=[])
        mock_datapush.get_agents_status = AsyncMock(return_value=status_collection)
        mock_context.datapush = mock_datapush
        mock_client.datapush = mock_datapush
        mock_client.singlesensor = mock_context

        # Mock system manager
        mock_system = MagicMock(name="system")
        mock_system.get_info = AsyncMock(
            return_value=stable_models.DeviceInfo.model_construct(
                serial_number="123456",
                serial="123456",
                mac_address="00:11:22:33:44:55",
                sw_version="5.9.2",
                fw_version="5.9.2",
                device_name="MockDevice",
                type="PC2",
                variant="S",
            )
        )
        mock_system.get_license_details = AsyncMock(return_value=MagicMock())
        mock_system.reboot = AsyncMock()
        mock_system.reset = AsyncMock()
        mock_system.get_state = AsyncMock(
            return_value=DeviceState1(
                status=stable_models.DeviceState.running,
                state=stable_models.State1.OK,
                details=stable_models.Details(
                    uptime_sec=100,
                    temperatures=stable_models.Temperatures(die=50, housing=40),
                ),
            )
        )
        mock_client.get_privacy_state = AsyncMock(return_value=1)
        mock_client.system = mock_system
        mock_context.system = mock_system

        # Mock privacy
        mock_privacy = MagicMock()
        mock_privacy.get_privacy_mode = AsyncMock(return_value=1)
        mock_context.privacy = mock_privacy

        # Mock network
        mock_network = MagicMock()
        mock_network.get_ipv4 = AsyncMock(return_value=stable_models.NetworkIpv4Settings.model_construct(address="127.0.0.1"))
        mock_network.get_ipv6 = AsyncMock(return_value=stable_models.NetworkIpv6Settings.model_construct(address="::1"))
        mock_network.get_state = AsyncMock(
            return_value=stable_models.NetworkState.model_construct(details=stable_models.Details2.model_construct(mac_address="00:11:22:33:44:55"))
        )
        mock_network.get_hostname = AsyncMock(return_value=stable_models.Hostname.model_construct(hostname="MockHost"))

        async def mock_update_hostname(h):
            mock_network.get_hostname.return_value = h

        mock_network.update_hostname = AsyncMock(side_effect=mock_update_hostname)
        mock_network.reset_ipv4 = AsyncMock()
        mock_network.reset_ipv6 = AsyncMock()
        mock_client.network = mock_network

        # Mock users
        mock_users = MagicMock()
        mock_users.get_all = AsyncMock(
            return_value=stable_models.UserDetails.model_construct(users=[stable_models.UserDetail.model_construct(id="admin", active=True)])
        )
        mock_users.get_current = AsyncMock(return_value=stable_models.UserDetail.model_construct(id="admin", active=True))
        mock_users.get_user = AsyncMock(side_effect=lambda id: stable_models.UserDetail.model_construct(id=id, active=True))
        mock_users.update_activation = AsyncMock()
        mock_users.reset_password = AsyncMock()
        mock_client.users = mock_users

        # Mock other managers to avoid await errors
        mock_client.time = MagicMock()
        mock_client.time.get_settings = AsyncMock(return_value=stable_models.TimeSettings.model_construct())
        mock_client.time.get_state = AsyncMock(
            return_value=stable_models.TimeState.model_construct(details=stable_models.Details3.model_construct(time_utc=1717200000000))
        )
        mock_client.time.get_zones = AsyncMock(return_value=stable_models.Timezones.model_construct(timezones=[]))
        mock_client.time.update_settings = AsyncMock()
        mock_client.time.reset_settings = AsyncMock()
        mock_context.time = mock_client.time

        mock_client.update = MagicMock()
        mock_client.update.get_status = AsyncMock(return_value=stable_models.UpdateInfo.model_construct(version="5.9.2", min_sw_version="5.0.0"))
        mock_client.update.upload_firmware = AsyncMock(
            return_value=stable_models.UpdateVersion.model_construct(version="5.10.0", build_date="2024-06-01")
        )
        mock_context.update = mock_client.update

        async def mock_update_config(c):
            mock_client.itxpt.get_config.return_value = c

        mock_client.itxpt = MagicMock()
        mock_client.itxpt.get_config = AsyncMock(return_value=stable_models.ItxptConfig.model_construct(itxpt_enabled=True))
        mock_client.itxpt.get_state = AsyncMock(return_value=stable_models.ItxptState.model_construct())
        mock_client.itxpt.get_services_state = AsyncMock(return_value=stable_models.ItxptServicesState.model_construct())
        mock_client.itxpt.update_config = AsyncMock(side_effect=mock_update_config)

        mock_client.history = MagicMock()
        mock_client.history.get_counts = AsyncMock(return_value=HistoryLogics.model_construct(measurements=[]))
        mock_context.history = mock_client.history

        mock_client.licenses = MagicMock()
        mock_client.licenses.get_proactive_license_probing = AsyncMock()
        mock_client.licenses.get_license_details = AsyncMock()

        mock_client.analytics = MagicMock()
        mock_client.analytics.get_all_logics = AsyncMock(return_value=stable_models.LogicCollection.model_construct(logics=[]))
        mock_client.analytics.get_all_modifiers = AsyncMock(return_value=stable_models.ModifierCollection.model_construct(modifiers=[]))
        mock_client.analytics.get_all_counters = AsyncMock(return_value=stable_models.CounterCollection.model_construct(counters=[]))
        mock_context.analytics = mock_client.analytics

        yield mock_client
    else:
        async with DeviceClient(host, user, password, max_retries=1) as client:
            yield client
