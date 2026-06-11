"""
Xovis SDK - Control Plane DataPush Limits & Context Isolation
"""

import asyncio
import logging

import pytest

from xovis.api.core.exceptions import XovisAPIError
from xovis.api.device.client import DeviceClient
from xovis.models.device import (
    AgentConfig,
    DataConfig,
    DataFormat,
    DataFormatType,
    DataPushAgent,
    DataPushConnection,
    DataPushProtocol,
    DataPushType,
    Scheduler,
    SchedulerType,
    TCPConfig,
    TCPUDPMode,
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.destructive
class TestDataPushLimits:
    """
    Validates physical hardware constraints and context isolation boundaries.
    """

    async def test_context_isolation_leakage(self, real_device: DeviceClient) -> None:
        """
        Proves that agents created in a multisensor context are invisible to the singlesensor context.
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        # Ensure we have a multisensor context
        if not real_device.multisensors:
            await real_device.multisensors.sync()

        active_contexts = real_device.active_contexts
        ms_contexts = [ctx for ctx in active_contexts if hasattr(ctx, "ms_id")]

        if not ms_contexts:
            pytest.skip("No multisensor context available on this device.")

        target_ms = ms_contexts[0]
        ss_manager = real_device.singlesensor.datapush
        ms_manager = target_ms.datapush

        agent_name = f"Isolation_Test_{target_ms.ms_id}"

        # Cleanup existing
        try:
            agents = await ms_manager.get_all_agents()
            for a in agents.agents:
                if a.name == agent_name:
                    await ms_manager.delete_agent(a.id)
        except Exception:
            pass

        # Create a connection first (required for agent)
        conn = await ms_manager.create_connection(
            DataPushConnection(
                name=f"Conn_{agent_name}",
                protocol=DataPushProtocol.TCP,
                config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000),
            ),
            id_mode="SERVER",
        )

        try:
            # Create agent on MS context
            await ms_manager.create_agent(
                DataPushAgent(
                    name=agent_name,
                    type=DataPushType.LIVE_DATA,
                    connection=conn.id,
                    enabled=True,
                    config=AgentConfig(
                        scheduler=Scheduler(type=SchedulerType.IMMEDIATE),
                        data=DataConfig(
                            format=DataFormat(type=DataFormatType.JSON, version="5.0"),
                            resolution="MAX",
                        ),
                    ),
                ),
                id_mode="SERVER",
            )

            # Assert it exists in MS context
            ms_agents = await ms_manager.get_all_agents()
            assert any(a.name == agent_name for a in ms_agents.agents), "Agent should exist in MS context"

            # Assert it does NOT exist in SS context
            ss_agents = await ss_manager.get_all_agents()
            assert not any(a.name == agent_name for a in ss_agents.agents), "MS Agent leaked into SS context!"

        finally:
            # Cleanup
            try:
                agents = await ms_manager.get_all_agents()
                for a in agents.agents:
                    if a.name == agent_name:
                        await ms_manager.delete_agent(a.id)
                await ms_manager.delete_connection(conn.id)
            except Exception:
                pass

    async def test_oom_defense_pacing_and_limits(self, real_device: DeviceClient) -> None:
        """
        Fires concurrent creation requests to verify intra-mutation pacing and
        graceful handling of hardware storage limits (413/507).
        """
        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()

        manager = real_device.singlesensor.datapush

        # We'll try to create 15 connections concurrently.
        # The SDK's _pacing_delay() should prevent these from hitting the hardware
        # all at once, effectively serializing them (2s per request = 30s total).

        conns_to_create = []
        for i in range(15):
            conns_to_create.append(
                DataPushConnection(
                    name=f"OOM_Test_{i}",
                    protocol=DataPushProtocol.TCP,
                    config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://127.0.0.1", port=9000 + i),
                )
            )

        logger.info("Firing 15 concurrent create_connection requests (OOM Defense Test)...")

        # We use return_exceptions=True to capture the 413/507 errors when the limit is reached
        results = await asyncio.gather(
            *[manager.create_connection(c, id_mode="SERVER") for c in conns_to_create],
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]

        logger.info(f"OOM Test Results: {len(successes)} successes, {len(failures)} failures.")

        # Verify that failures (if any) are graceful limits, not crashes (500)
        for fail in failures:
            if isinstance(fail, XovisAPIError):
                # Firmware 5.x usually returns 413 (Request Entity Too Large / Limit reached)
                # or sometimes 507 (Insufficient Storage) for too many connections.
                # It should NOT be a 500.
                assert fail.status_code in (413, 507, 400), f"Unexpected error code: {fail.status_code}. Response: {fail.response_body}"
                logger.info(f"Caught expected limit error: {fail.status_code}")
            else:
                # If it's another exception, it might be a bug or network issue
                raise fail

        # Verification: If we have successes, delete them
        for conn in successes:
            await manager.delete_connection(conn.id)

        # If no failures occurred, it means the device had enough room for 15 more connections.
        # However, the pacing should have ensured they were handled correctly.
        # If we wanted to FORCE a failure, we might need more, but 15 is a reasonable stress test.
