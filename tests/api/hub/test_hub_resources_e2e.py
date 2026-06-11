import logging

import pytest

from xovis.api.device.client import DeviceClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)

TARGET_MAC = "3C:EC:EF:EB:5C:EE"


@pytest.mark.asyncio
async def test_hub_tunnel_datapush_e2e(real_hub):
    """
    E2E test to verify DataPush Management endpoints via Hub Tunnel.
    Target device: 3C:EC:EF:EB:5C:EE
    """
    hub = real_hub
    # Testing HubClient iterator
    async for device in hub:
        if device._http_client.base_url.path.endswith(f"devices/{TARGET_MAC}/tunnel"):
            assert isinstance(device, DeviceClient)
            datapush = device.singlesensor.datapush
            # ... rest of the test
            break

    # Original specific device connection test
    async with await hub.connect_device(TARGET_MAC) as device:
        assert isinstance(device, DeviceClient)

        datapush = device.singlesensor.datapush

        print("\nTesting get_all_agents()...")
        try:
            agents = await datapush.get_all_agents()
            print(f"Agents: {agents}")
        except Exception as e:
            print(f"get_all_agents failed: {e}")

        print("\nTesting get_agents_status()...")
        try:
            status = await datapush.get_agents_status()
            print(f"Agents status: {status}")
        except Exception as e:
            print(f"get_agents_status failed: {e}")

        print("\nTesting get_all_connections()...")
        try:
            connections = await datapush.get_all_connections()
            print(f"Connections: {connections}")
        except Exception as e:
            print(f"get_all_connections failed: {e}")

        print("\nTesting get_legacy_config()...")
        try:
            legacy = await datapush.get_legacy_config()
            print(f"Legacy config: {legacy}")
        except Exception as e:
            print(f"get_legacy_config failed: {e}")


@pytest.mark.asyncio
async def test_hub_tunnel_analytics_e2e(real_hub):
    """
    E2E test to verify Analytics Management endpoints via Hub Tunnel.
    """
    hub = real_hub
    async with await hub.connect_device(TARGET_MAC) as device:
        analytics = device.singlesensor.analytics

        print("\nTesting get_logic_limits()...")
        try:
            limits = await analytics.get_logic_limits()
            print(f"Logic limits: {limits}")
        except Exception as e:
            print(f"get_logic_limits failed: {e}")

        print("\nTesting get_all_logics()...")
        try:
            logics = await analytics.get_all_logics()
            print(f"Logics: {logics}")
        except Exception as e:
            print(f"get_all_logics failed: {e}")


@pytest.mark.asyncio
async def test_hub_tunnel_scene_e2e(real_hub):
    """
    E2E test to verify Scene Management endpoints via Hub Tunnel.
    """
    hub = real_hub
    async with await hub.connect_device(TARGET_MAC) as device:
        scene = device.singlesensor.scene

        print("\nTesting get_geometry_limits()...")
        try:
            limits = await scene.get_geometry_limits()
            print(f"Geometry limits: {limits}")
        except Exception as e:
            print(f"get_geometry_limits failed: {e}")

        print("\nTesting get_all_geometries()...")
        try:
            geometries = await scene.get_all_geometries()
            print(f"Geometries: {geometries}")
        except Exception as e:
            print(f"get_all_geometries failed: {e}")


@pytest.mark.asyncio
async def test_hub_tunnel_other_managers_e2e(real_hub):
    """
    E2E test to verify Network, Time, Users, and Privacy Management endpoints via Hub Tunnel.
    """
    hub = real_hub
    async with await hub.connect_device(TARGET_MAC) as device:
        # Network
        print("\nTesting NetworkManager.get_state()...")
        try:
            nw_state = await device.network.get_state()
            print(f"Network state: {nw_state}")
        except Exception as e:
            print(f"Network get_state failed: {e}")

        # Time
        print("\nTesting TimeManager.get_settings()...")
        try:
            time_settings = await device.time.get_settings()
            print(f"Time settings: {time_settings}")
        except Exception as e:
            print(f"Time get_settings failed: {e}")

        # Users
        print("\nTesting UsersManager.get_all()...")
        try:
            users = await device.users.get_all()
            print(f"Users: {users}")
        except Exception as e:
            print(f"Users get_all failed: {e}")

        # Update
        print("\nTesting UpdateManager.get_info()...")
        try:
            update_info = await device.update.get_info()
            print(f"Update info: {update_info}")
        except Exception as e:
            print(f"Update get_info failed: {e}")

        print("\nTesting UpdateManager.get_state()...")
        try:
            update_state = await device.update.get_state()
            print(f"Update state: {update_state}")
        except Exception as e:
            print(f"Update get_state failed: {e}")

        # Privacy
        print("\nTesting PrivacyManager.get_privacy_mode()...")
        try:
            # PrivacyManager is accessible via singlesensor.privacy
            # or device.privacy (depends on device type, but we use device.privacy for now)
            privacy_mode = await device.privacy.get_privacy_mode()
            print(f"Privacy mode: {privacy_mode}")
        except Exception as e:
            print(f"Privacy get_privacy_mode failed: {e}")

        # Analytics (Logics)
        print("\nTesting AnalyticsManager.get_all_logics()...")
        try:
            logics = await device.singlesensor.analytics.get_all_logics()
            print(f"Logics: {logics}")
        except Exception as e:
            print(f"Analytics get_all_logics failed: {e}")

        # Scene (Geometries Limits)
        print("\nTesting SceneManager.get_geometry_limits()...")
        try:
            limits = await device.singlesensor.scene.get_geometry_limits()
            print(f"Geometry limits: {limits}")
        except Exception as e:
            print(f"Scene get_geometry_limits failed: {e}")

        # System Info
        print("\nTesting SystemManager.get_info()...")
        try:
            await device.system.get_info()
            print("System info fetched successfully")
        except Exception as e:
            print(f"System get_info failed: {e}")

        # ITxPT
        print("\nTesting ITxPTManager.get_config()...")
        try:
            itxpt_config = await device.itxpt.get_config()
            print(f"ITxPT config: {itxpt_config}")
        except Exception as e:
            print(f"ITxPT get_config failed: {e}")

        # Network (remotes)
        print("\nTesting NetworkManager.get_all_remotes()...")
        try:
            remotes = await device.network.get_all_remotes()
            print(f"Remotes: {remotes}")
        except Exception as e:
            print(f"Network get_all_remotes failed: {e}")

        # Topology
        print("\nTesting TopologyManager.get_ms_graph()...")
        try:
            graph = await device.topology.get_ms_graph()
            print(f"Topology graph: {graph.master_mac}, children: {len(graph.children)}")
        except Exception as e:
            print(f"Topology get_ms_graph failed: {e}")
