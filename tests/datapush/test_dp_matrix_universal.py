"""
Xovis SDK - DataPlane Stream Protocol Validation Matrix
"""

import asyncio
import logging
import uuid
from typing import Any

import pytest

from tests.datapush.dp_validation_sink import ValidationSink
from xovis.api.device.client import DeviceClient
from xovis.models.device import (
    AgentConfig,
    DataConfig,
    DataFormat,
    DataFormatType,
    DataPushAgent,
    DataPushConnection,
    DataPushFilters,
    DataPushProtocol,
    DataPushTriggerConfig,
    DataPushTriggerType,
    DataPushType,
    HTTPAuthMethod,
    HTTPConfig,
    IntervalType,
    RetryConfig,
    RetryMode,
    Scheduler,
    SchedulerType,
    TCPConfig,
    TCPUDPMode,
    UDPConfig,
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.destructive
class TestDataPlaneStreamMatrix:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "agent_type, protocol, scheduler_cfg, retry_mode, filters_cfg, http_auth",
        [
            (
                DataPushType.LIVE_DATA,
                DataPushProtocol.TCP,
                {"type": SchedulerType.IMMEDIATE},
                RetryMode.DROP,
                {
                    "included_objects": ["PERSON", "BICYCLE", "PRAM", "WHEELCHAIR"],
                    "filter_events_by_objects": True,
                    "included_scene_events": ["ZONE_ENTRY"],
                    "included_count_events": "NONE",
                    "included_info_events": "NONE",
                },
                HTTPAuthMethod.NONE,
            ),
            (
                DataPushType.LOGICS,
                DataPushProtocol.HTTP,
                {"type": SchedulerType.INTERVAL, "interval": IntervalType.ONE_MINUTE},
                RetryMode.INCREASING_DELAY,
                {"included_logics": "ALL"},
                HTTPAuthMethod.BEARER_TOKEN,
            ),
            (
                DataPushType.STATUS,
                DataPushProtocol.UDP,
                {"type": SchedulerType.INTERVAL, "interval": IntervalType.FIVE_SECONDS},
                RetryMode.INTERVAL,
                {},
                HTTPAuthMethod.NONE,
            ),
            (
                DataPushType.WIFI_BT,
                DataPushProtocol.HTTP,
                {"type": SchedulerType.INTERVAL, "interval": IntervalType.FIVE_SECONDS},
                RetryMode.INCREASING_DELAY_EXPONENTIAL,
                {},
                HTTPAuthMethod.BASIC,
            ),
            (
                DataPushType.RECORDING,
                DataPushProtocol.HTTP,
                {"type": SchedulerType.INTERVAL, "interval": IntervalType.ONE_MINUTE},
                RetryMode.INCREASING_DELAY_EXPONENTIAL,
                {},
                HTTPAuthMethod.NONE,
            ),
            (
                DataPushType.LIVE_DATA,
                DataPushProtocol.HTTP,
                {"type": SchedulerType.IMMEDIATE},
                RetryMode.DROP,
                {
                    "included_objects": "ALL",
                    "filter_events_by_objects": False,
                    "included_scene_events": "ALL",
                    "included_count_events": "ALL",
                    "included_info_events": "ALL",
                },
                HTTPAuthMethod.NONE,
            ),
        ],
    )
    async def test_high_frequency_telemetry_matrix(
        self,
        real_device,
        tcp_server,
        udp_server,
        http_server,
        local_routing_ip: str,
        agent_type: DataPushType,
        protocol: DataPushProtocol,
        scheduler_cfg: dict[str, Any],
        retry_mode: RetryMode,
        filters_cfg: dict[str, Any],
        http_auth: HTTPAuthMethod,
    ) -> None:
        """
        Validates high-frequency Data Plane telemetry performance against diverse
        connection pipelines and scheduler configurations on target hardware.

        Verifies resilient payload transmission, rigorous latency parameters, HTTP
        webhook behaviors, raw socket ingest capabilities, and deep payload constraints
        (Sequence ID monotonicity, MAC alignment).
        """
        logger.setLevel(logging.DEBUG)

        if hasattr(real_device, "__anext__"):
            real_device = await real_device.__anext__()
        elif hasattr(real_device, "__aenter__") and not isinstance(real_device, DeviceClient):
            # If it's a mock that hasn't been entered yet
            real_device = await real_device.__aenter__()

        if hasattr(tcp_server, "__anext__"):
            tcp_server = await tcp_server.__anext__()
        elif hasattr(tcp_server, "__aenter__"):
            tcp_server = await tcp_server.__aenter__()

        if hasattr(udp_server, "__anext__"):
            udp_server = await udp_server.__anext__()
        elif hasattr(udp_server, "__aenter__"):
            udp_server = await udp_server.__aenter__()

        # Determine if we are in mock mode
        is_mock = hasattr(real_device, "mock_calls")
        if is_mock:
            pytest.skip("High-frequency telemetry matrix requires real hardware for stream validation.")

        has_wifi = await real_device.has_wifi()
        has_analytics = await real_device.has_analytics()
        logger.info(f"Capability Check - WiFi: {has_wifi}, Analytics: {has_analytics}")

        if agent_type in (DataPushType.WIFI_BT, DataPushType.STATUS):
            if not has_wifi and agent_type == DataPushType.WIFI_BT:
                pytest.skip("Target hardware lacks WIFI capabilities.")

        if agent_type != DataPushType.STATUS and not has_analytics:
            pytest.skip(f"Target hardware lacks analytics support (WiFi: {has_wifi}, Analytics: {has_analytics})")

        from xovis.api.core.exceptions import XovisAuthError

        try:
            privacy_mode = await real_device.get_privacy_state()
            logger.info(f"Privacy Mode Check: {privacy_mode}")
            if privacy_mode in ("3", "4", 3, 4):
                pytest.skip(f"Data extraction blocked by Edge Privacy Policy (Mode {privacy_mode}).")
        except XovisAuthError as e:
            if "Details: <!DOCTYPE html>" in str(e):
                pytest.skip(f"Access Restricted: Cloud Proxy Firewall or Strict Privacy Mode is blocking data extraction. Details: {e}")
            raise e

        for context in real_device.active_contexts:
            manager = context.datapush

            is_multisensor = hasattr(context, "ms_id")
            if agent_type == DataPushType.STATUS and is_multisensor:
                logger.info(f"Skipping STATUS push for context {getattr(context, 'id', 'unknown')} as it is a Multisensor context")
                continue

            expected_mac = getattr(context, "mac_address", None) or getattr(real_device, "mac_address", None)

            sink = ValidationSink(agent_type=str(agent_type.value), expected_mac=expected_mac)

            conn_id = 5000 + (hash(str(agent_type)) % 1000)
            agent_id = 5000 + (hash(str(protocol)) % 1000)

            resolution = "MAX"
            if agent_type == DataPushType.LOGICS:
                resolution = "ONE_MINUTE"
            elif agent_type == DataPushType.WIFI_BT:
                resolution = "ONE_SECOND"

            try:
                existing_agents = await manager.get_all_agents()
                for a in existing_agents.agents:
                    if a.id == agent_id or "E2E_Matrix_Agent" in (a.name or ""):
                        await manager.delete_agent(a.id)
            except Exception:
                pass

            try:
                existing_conns = await manager.get_all_connections()
                for c in existing_conns.connections:
                    if c.id == conn_id or "E2E_Matrix_Conn" in (c.name or ""):
                        await manager.delete_connection(c.id)
            except Exception:
                pass

            await asyncio.sleep(3.0)

            try:
                if protocol == DataPushProtocol.TCP:
                    tcp_server.attach_sink(sink)
                    tcp_uri = f"tcp://{local_routing_ip}" if not local_routing_ip.startswith("tcp://") else local_routing_ip
                    conn_config = TCPConfig(mode=TCPUDPMode.CLIENT, uri=tcp_uri, port=9000)
                elif protocol == DataPushProtocol.UDP:
                    udp_server.attach_sink(sink)
                    udp_uri = f"udp://{local_routing_ip}" if not local_routing_ip.startswith("udp://") else local_routing_ip
                    conn_config = UDPConfig(mode=TCPUDPMode.CLIENT, uri=udp_uri, port=9002)
                else:
                    http_server.attach_sink(sink)
                    http_cfg = HTTPConfig(
                        uri=f"http://{local_routing_ip}/webhook",
                        port=9001,
                        auth_method=http_auth,
                        chunked_transfer_enabled=False,
                    )

                    if http_auth == HTTPAuthMethod.BEARER_TOKEN:
                        http_server.expected_token = "matrix_secret"
                        http_cfg.auth_data = "matrix_secret"
                    elif http_auth == HTTPAuthMethod.BASIC:
                        http_cfg.user = "matrix_user"
                        http_cfg.password = "matrix_pass"
                        http_server.expected_user = "matrix_user"
                        http_server.expected_password = "matrix_pass"

                    http_cfg.connection_timeout_s = 10.0
                    conn_config = http_cfg
            except Exception as e:
                pytest.fail(f"Failed to prepare connection config: {e}")

            agent_filters = DataPushFilters.model_validate(filters_cfg) if filters_cfg else None

            created_agent_id = None
            created_conn_id = None

            try:
                connection = await manager.create_connection(
                    DataPushConnection(
                        name=f"E2E_Matrix_Conn_{uuid.uuid4().hex[:4]}",
                        protocol=protocol,
                        config=conn_config,
                    ),
                    id_mode="SERVER",
                )
                created_conn_id = connection.id

                format_type = DataFormatType.JSON
                if agent_type == DataPushType.RECORDING:
                    format_type = DataFormatType.RECORDING

                retry_cfg = RetryConfig(mode=retry_mode)
                if agent_type == DataPushType.RECORDING:
                    retry_cfg = RetryConfig(
                        mode=RetryMode.INCREASING_DELAY_EXPONENTIAL,
                        max_number=12,
                        reset_on_next_push_schedule=True,
                        delay_start_min=2.0,
                        delay_start_max=2.0,
                        delay_increase_factor=2.0,
                    )

                agent = await manager.create_agent(
                    DataPushAgent(
                        name=f"E2E_Matrix_Agent_{uuid.uuid4().hex[:4]}",
                        type=agent_type,
                        connection=created_conn_id,
                        enabled=True,
                        config=AgentConfig(
                            scheduler=Scheduler(
                                type=scheduler_cfg["type"],
                                interval=scheduler_cfg.get("interval"),
                                retry=retry_cfg,
                            ),
                            data=DataConfig(
                                format=DataFormat(type=format_type, version="5.0"),
                                resolution=resolution,
                                package_size=1,
                                include_empty=True,
                            ),
                            filters=agent_filters,
                        ),
                    ),
                    id_mode="SERVER",
                )
                logger.info(f"Created agent {agent.id}: {agent.model_dump_json(by_alias=True, exclude_unset=True)}")
                created_agent_id = agent.id

                await asyncio.sleep(2.0)

                if scheduler_cfg.get("type") == SchedulerType.INTERVAL:
                    if agent_type in (DataPushType.STATUS, DataPushType.RECORDING):
                        logger.info(f"Skipping trigger for {agent_type} (not supported by hardware)")
                    else:
                        from datetime import datetime, timedelta, timezone

                        now = datetime.now(timezone.utc)
                        aligned_to = now.replace(second=0, microsecond=0)

                        aligned_from = aligned_to - timedelta(minutes=60)

                        trigger = DataPushTriggerConfig(
                            type=DataPushTriggerType.TIME_RANGE,
                            time_from=int(aligned_from.timestamp() * 1000),
                            time_to=int(aligned_to.timestamp() * 1000),
                        )
                        logger.info(f"Triggering {agent_type} agent {created_agent_id} for recovery...")
                        await manager.trigger_agent_push(created_agent_id, trigger)
                elif scheduler_cfg.get("type") == SchedulerType.IMMEDIATE:
                    logger.info(f"Agent {created_agent_id} (IMMEDIATE) created. Waiting for live data stream...")

                test_timeout = 30.0
                if agent_type == DataPushType.RECORDING:
                    test_timeout = 240.0

                await asyncio.wait_for(sink.frame_received.wait(), timeout=test_timeout)

                async with sink.lock:
                    assert sink.total_frames > 0
                    payload_keys = sink.latest_frame.keys()

                    if agent_type == DataPushType.LIVE_DATA:
                        assert "live_data" in payload_keys
                    elif agent_type == DataPushType.LOGICS:
                        assert "logics_data" in payload_keys
                    elif agent_type == DataPushType.STATUS:
                        assert "status_data" in payload_keys
                    elif agent_type == DataPushType.RECORDING:
                        assert any(k in payload_keys for k in ["recording_data", "validation_recording", "binary_data"])
                    elif agent_type == DataPushType.WIFI_BT:
                        assert "wifi_bt_data" in payload_keys
            finally:
                if created_agent_id is not None:
                    try:
                        await manager.delete_agent(created_agent_id)
                    except Exception:
                        pass
                if created_conn_id is not None:
                    try:
                        await manager.delete_connection(created_conn_id)
                    except Exception:
                        pass

                await asyncio.sleep(1.0)

            await asyncio.sleep(5.0)
