"""
Xovis SDK - Control Plane DataPush Triggers & Recovery
"""

import logging

import httpx
import pytest

from xovis.api.device.client import DeviceClient
from xovis.models.device import (
    AgentConfig,
    DataConfig,
    DataFormat,
    DataFormatType,
    DataPushAgent,
    DataPushConnection,
    DataPushProtocol,
    DataPushTriggerConfig,
    DataPushTriggerType,
    DataPushType,
    IntervalType,
    RetryConfig,
    RetryMode,
    Scheduler,
    SchedulerType,
    TCPConfig,
    TCPUDPMode,
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.destructive
class TestDataPushTriggers:
    """
    Validates the trigger_agent_push and test_connection REST endpoints,
    including SDK guardrails and firmware bug regression checks.
    """

    async def test_sdk_trigger_guardrail(self, real_device: DeviceClient, caplog) -> None:
        """
        Asserts that calling manager.trigger_agent_push() on a STATUS or RECORDING
        agent is intercepted by the SDK, returning an IDLE status and logging a warning.
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        is_mock = hasattr(real_device, "mock_calls")

        manager = real_device.singlesensor.datapush

        # Create a connection
        conn = await manager.create_connection(
            DataPushConnection(
                name="Trigger_Guard_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        agent_id = None
        try:
            # Create a STATUS agent (which is forbidden from triggering)
            agent = await manager.create_agent(
                DataPushAgent(
                    name="Trigger_Guard_Agent",
                    type=DataPushType.STATUS,
                    connection=conn.id if not is_mock else 9999,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(
                            type=SchedulerType.INTERVAL,
                            interval=IntervalType.ONE_MINUTE,
                            retry=RetryConfig(
                                mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                                max_number=12,
                                reset_on_next_push_schedule=True,
                                delay_start_min=2.0,
                                delay_start_max=2.0,
                                delay_increase_factor=2.0,
                            ),
                        ),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.JSON, version="5.0"),
                            resolution="ONE_MINUTE",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )
            agent_id = agent.id

            with caplog.at_level(logging.WARNING):
                trigger_config = DataPushTriggerConfig(type=DataPushTriggerType.ALL)
                status = await manager.trigger_agent_push(agent_id, trigger_config)

                # Assert SDK intercepted and returned IDLE
                assert status.status == "IDLE"
                if not is_mock:
                    assert "Manual retriggering is not supported" in caplog.text

        finally:
            if agent_id:
                await manager.delete_agent(agent_id)
            await manager.delete_connection(conn.id)

    @pytest.mark.skip(reason="CRITICAL: Triggers FW bug causing sensor reboot. Enable manually to check for Xovis patches.")
    async def test_firmware_trigger_bug_quarantined(self, real_device: DeviceClient) -> None:
        """
        Bypasses the SDK and sends a raw HTTP POST directly to the trigger endpoint
        for a RECORDING agent. This is known to crash certain firmware versions.
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        manager = real_device.singlesensor.datapush

        # Create a connection
        conn = await manager.create_connection(
            DataPushConnection(
                name="Bug_Check_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        agent_id = None
        try:
            # Create a RECORDING agent
            agent = await manager.create_agent(
                DataPushAgent(
                    name="Bug_Check_Agent",
                    type=DataPushType.RECORDING,
                    connection=conn.id,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(
                            type=SchedulerType.INTERVAL,
                            interval=IntervalType.ONE_MINUTE,
                            retry=RetryConfig(
                                mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                                max_number=12,
                                reset_on_next_push_schedule=True,
                                delay_start_min=2.0,
                                delay_start_max=2.0,
                                delay_increase_factor=2.0,
                            ),
                        ),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.RECORDING, version="5.0"),
                            resolution="MAX",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )
            agent_id = agent.id

            # Bypass SDK - Get raw client details
            # We assume DeviceClient has an internal httpx client or similar
            base_url = real_device._http.base_url
            path = f"{manager._resolve_path()}/agents/{agent_id}/trigger"

            # Use raw POST
            async with httpx.AsyncClient(verify=False) as client:
                # We need auth here if it's not handled by the client
                # For simplicity in this test, we try to use the existing client's auth if possible
                # But since we are bypassing, we might need to copy headers.
                headers = real_device._http.headers
                response = await client.post(f"{base_url}{path}", json={"type": "ALL"}, headers=headers)

                # If the sensor reboots, this will likely time out or return a connection error.
                assert response.status_code == 200

        finally:
            if agent_id:
                try:
                    await manager.delete_agent(agent_id)
                except Exception:
                    pass
            try:
                await manager.delete_connection(conn.id)
            except Exception:
                pass

    async def test_trigger_recovery_last_package(self, real_device: DeviceClient) -> None:
        """
        Ensures LAST_PACKAGE recovery mechanism works on a valid agent type (LOGICS).
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        # Determine if we are in mock mode
        is_mock = hasattr(real_device, "mock_calls")

        manager = real_device.singlesensor.datapush

        # Create a connection
        conn = await manager.create_connection(
            DataPushConnection(
                name="Recovery_LP_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        agent_id = None
        try:
            # Create a LOGICS agent
            agent = await manager.create_agent(
                DataPushAgent(
                    name="Recovery_LP_Agent",
                    type=DataPushType.LOGICS,
                    connection=conn.id if not is_mock else 9999,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(
                            type=SchedulerType.INTERVAL,
                            interval=IntervalType.ONE_MINUTE,
                            retry=RetryConfig(
                                mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                                max_number=12,
                                reset_on_next_push_schedule=True,
                                delay_start_min=2.0,
                                delay_start_max=2.0,
                                delay_increase_factor=2.0,
                            ),
                        ),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.JSON, version="5.0"),
                            resolution="ONE_MINUTE",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )
            agent_id = agent.id

            trigger_config = DataPushTriggerConfig(type=DataPushTriggerType.LAST_PACKAGE)
            status = await manager.trigger_agent_push(agent_id, trigger_config)

            # It might be BUSY or IDLE depending on how fast it finishes
            assert status.status in ("BUSY", "IDLE")

        finally:
            if agent_id:
                await manager.delete_agent(agent_id)
            await manager.delete_connection(conn.id)

    async def test_trigger_recovery_all(self, real_device: DeviceClient) -> None:
        """
        Ensures ALL recovery mechanism works on a valid agent type (LOGICS).
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        # Determine if we are in mock mode
        is_mock = hasattr(real_device, "mock_calls")

        manager = real_device.singlesensor.datapush

        # Create a connection
        conn = await manager.create_connection(
            DataPushConnection(
                name="Recovery_All_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        agent_id = None
        try:
            # Create a LOGICS agent
            agent = await manager.create_agent(
                DataPushAgent(
                    name="Recovery_All_Agent",
                    type=DataPushType.LOGICS,
                    connection=conn.id if not is_mock else 9999,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(
                            type=SchedulerType.INTERVAL,
                            interval=IntervalType.ONE_MINUTE,
                            retry=RetryConfig(
                                mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                                max_number=12,
                                reset_on_next_push_schedule=True,
                                delay_start_min=2.0,
                                delay_start_max=2.0,
                                delay_increase_factor=2.0,
                            ),
                        ),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.JSON, version="5.0"),
                            resolution="ONE_MINUTE",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )
            agent_id = agent.id

            trigger_config = DataPushTriggerConfig(type=DataPushTriggerType.ALL)
            status = await manager.trigger_agent_push(agent_id, trigger_config)

            assert status.status in ("BUSY", "IDLE")

        finally:
            if agent_id:
                await manager.delete_agent(agent_id)
            await manager.delete_connection(conn.id)

    async def test_trigger_recovery_dummy_data(self, real_device: DeviceClient) -> None:
        """
        Ensures the DUMMY_DATA recovery mechanism works, which requires a specific payload.
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        # Determine if we are in mock mode
        is_mock = hasattr(real_device, "mock_calls")

        manager = real_device.singlesensor.datapush

        # Create a connection
        conn = await manager.create_connection(
            DataPushConnection(
                name="Recovery_Dummy_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        agent_id = None
        try:
            # Create a LOGICS agent
            agent = await manager.create_agent(
                DataPushAgent(
                    name="Recovery_Dummy_Agent",
                    type=DataPushType.LOGICS,
                    connection=conn.id if not is_mock else 9999,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(
                            type=SchedulerType.INTERVAL,
                            interval=IntervalType.ONE_MINUTE,
                            retry=RetryConfig(
                                mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                                max_number=12,
                                reset_on_next_push_schedule=True,
                                delay_start_min=2.0,
                                delay_start_max=2.0,
                                delay_increase_factor=2.0,
                            ),
                        ),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.JSON, version="5.0"),
                            resolution="ONE_MINUTE",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )
            agent_id = agent.id

            trigger_config = DataPushTriggerConfig(type=DataPushTriggerType.DUMMY_DATA, file_name_prefix="sdk_test")
            status = await manager.trigger_agent_push(agent_id, trigger_config)

            assert status.status in ("BUSY", "IDLE")

        finally:
            if agent_id:
                await manager.delete_agent(agent_id)
            await manager.delete_connection(conn.id)

    async def test_preflight_connection_diagnostics(self, real_device: DeviceClient) -> None:
        """
        Validates the pre-flight `test_connection` endpoint used by deployment agents.
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        manager = real_device.singlesensor.datapush

        # Connection pointing to a non-routable blackhole
        blackhole_conn = await manager.create_connection(
            DataPushConnection(
                name="Blackhole_Conn",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(
                    mode=TCPUDPMode.CLIENT,
                    uri="tcp://10.255.255.255",
                    port=55555,
                    connection_timeout_s=1.0,
                ),
            ),
            id_mode="SERVER",
        )

        try:
            # Test Blackhole (Should Fail gracefully with NOT_CONNECTED or similar)
            fail_resp = await manager.test_connection(blackhole_conn.id)
            assert fail_resp.status in ("NOT_CONNECTED", "CLIENT_ERROR", "SERVER_ERROR")

        finally:
            await manager.delete_connection(blackhole_conn.id)
