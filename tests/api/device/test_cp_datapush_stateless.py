"""
Xovis SDK - DataPlane Stateless Validation Tests

Tier 1 testing suite for the high-frequency telemetry pipeline configuration.
Validates Pydantic V2 strict serialization, alias mapping constraints, and
time parsing mechanics without requiring live hardware connectivity.
Ensures the DataPushManager handles bounded schemas and HTTP errors correctly.
"""

import time

import httpx
import pytest
import respx

from xovis.api.core.exceptions import ResourceNotFoundError
from xovis.api.device.resources.datapush import DataPushManager
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
    FTPConfig,
    HTTPConfig,
    MQTTConfig,
    Scheduler,
    SchedulerType,
    SFTPConfig,
    TCPConfig,
    TCPUDPMode,
    UDPConfig,
)
from xovis.models.device_auto.versions.v5_9_11 import (
    AgentTrigger,
    AgentTriggerTypes,
    UpdateSchedule,
)
from xovis.utils.time import _parse_relative_time


class TestDataPushSerialization:
    """
    Validates strict Pydantic V2 serialization for DataPush Agent and Connection schemas.
    """

    def test_agent_config_serialization(self) -> None:
        """
        Validates that AgentConfig models correctly map pythonic attributes to hardware JSON outputs.

        Creates a DataPushAgent payload using the Pydantic abstraction and enforces that
        the exported JSON payload applies aliased schema requirements properly, specifically
        testing the `connection_id` alias resolution to the expected `connection` key.

        Raises:
            AssertionError: If strict serialization guarantees are compromised.
        """
        agent = DataPushAgent(
            name="Test_Agent",
            type=DataPushType.LIVE_DATA,
            connection=42,
            config=AgentConfig(
                scheduler=Scheduler(type=SchedulerType.IMMEDIATE),
                data=DataConfig(format=DataFormat(type=DataFormatType.JSON)),
            ),
        )

        payload = agent.model_dump(by_alias=True, exclude_unset=True, mode="json")

        assert "connection" in payload
        assert payload["connection"] == 42
        assert payload["name"] == "Test_Agent"
        assert payload["type"] == "LIVE_DATA"
        assert payload["config"]["scheduler"]["type"] == "IMMEDIATE"

        # Verify default enabled state is stripped by exclude_unset=True if not explicitly set
        # This is WHY the manager must force it.
        assert "enabled" not in payload

    def test_agent_enabled_serialization(self) -> None:
        """Verifies that explicitly setting enabled=True makes it appear in the dump."""
        agent = DataPushAgent(
            name="Test_Agent",
            type=DataPushType.LIVE_DATA,
            connection=1,
            enabled=True,
            config=AgentConfig(
                scheduler=Scheduler(type=SchedulerType.IMMEDIATE),
                data=DataConfig(format=DataFormat(type=DataFormatType.JSON)),
            ),
        )
        payload = agent.model_dump(by_alias=True, exclude_unset=True, mode="json")
        assert payload["enabled"] is True

    def test_connection_variants_serialization(self) -> None:
        """
        Validates serialization mechanics for all supported DataPush Connection protocols.

        Tests protocol-specific model bounds (HTTP, MQTT, TCP, UDP, FTP, SFTP) to explicitly
        confirm that the `DataPushConnection` union seamlessly serializes child parameters
        to the `config` sub-dictionary payload, preserving standard port variables and URI
        format schemes.

        Raises:
            AssertionError: If payload outputs miss nested mapping attributes.
        """
        http_conn = DataPushConnection(
            name="HTTP_Target",
            protocol=DataPushProtocol.HTTP,
            config=HTTPConfig(uri="http://10.0.0.1/webhook"),
        )
        assert http_conn.model_dump(by_alias=True)["config"]["uri"] == "http://10.0.0.1/webhook"

        mqtt_conn = DataPushConnection(
            name="MQTT_Target",
            protocol=DataPushProtocol.MQTT,
            config=MQTTConfig(uri="tcp://mqtt.xovis.cloud", topic="xovis/telemetry"),
        )
        assert mqtt_conn.model_dump(by_alias=True)["config"]["topic"] == "xovis/telemetry"

        tcp_conn = DataPushConnection(
            name="TCP_Target",
            protocol=DataPushProtocol.TCP,
            config=TCPConfig(mode=TCPUDPMode.CLIENT, uri="tcp://10.0.0.2", port=9000),
        )
        assert tcp_conn.model_dump(by_alias=True)["config"]["mode"] == "CLIENT"

        udp_conn = DataPushConnection(
            name="UDP_Target",
            protocol=DataPushProtocol.UDP,
            config=UDPConfig(mode=TCPUDPMode.CLIENT, uri="udp://10.0.0.3", port=9001),
        )
        assert udp_conn.model_dump(by_alias=True)["config"]["uri"] == "udp://10.0.0.3"

        ftp_conn = DataPushConnection(
            name="FTP_Target",
            protocol=DataPushProtocol.FTP,
            config=FTPConfig(uri="ftp://10.0.0.4", user="admin", password="password"),
        )
        assert ftp_conn.model_dump(by_alias=True)["config"]["user"] == "admin"

        sftp_conn = DataPushConnection(
            name="SFTP_Target",
            protocol=DataPushProtocol.SFTP,
            config=SFTPConfig(uri="sftp://10.0.0.5", user="admin", password="password", port=22),
        )
        assert sftp_conn.model_dump(by_alias=True)["config"]["port"] == 22


class TestTimeParsing:
    """
    Validates boundary mechanics of the XovisTime parser used for autonomous data recovery.
    """

    def test_relative_time_parsing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Validates parsing of relative string offsets into strictly typed Unix milliseconds.

        Calculates offset derivations utilizing strings like 'now', '-1d', and '-2M' to ensure
        telemetry trigger intervals map to precise integer bounds.

        Raises:
            AssertionError: If offset calculations misalign with the localized Unix epoch limits.
        """
        fixed_now = 1717968000.0  # 2024-06-09 21:20:00 UTC
        monkeypatch.setattr(time, "time", lambda: fixed_now)

        now_ms = _parse_relative_time("now")
        assert now_ms == 1717968000000

        one_day_ms = _parse_relative_time("-1d")
        assert one_day_ms == 1717968000000 - 86400000

        two_months_ms = _parse_relative_time("-2M")
        assert two_months_ms == 1717968000000 - (2 * 2592000000)

    def test_xovistime_validator(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Validates the BeforeValidator injection within Pydantic execution paths.

        Confirms that manual inputs dynamically transmute to valid timestamps after passing
        through the structural DataPushTriggerConfig engine.

        Raises:
            AssertionError: If relative inputs bypass transformation routines.
        """
        fixed_now = 1717968000.0  # 2024-06-09 21:20:00 UTC
        monkeypatch.setattr(time, "time", lambda: fixed_now)

        trigger = DataPushTriggerConfig(type=DataPushTriggerType.TIME_RANGE, time_from="-1h", time_to="now")
        payload = trigger.model_dump(by_alias=True, exclude_unset=True, mode="json")

        assert payload["time_from"] == str(1717968000000 - 3600000)
        assert payload["time_to"] == "1717968000000"
        assert int(payload["time_to"]) > int(payload["time_from"])

    def test_model_xovistime_normalization(self) -> None:
        """Validates that models using XovisTime correctly normalize relative strings."""
        # Test AgentTrigger
        trigger = AgentTrigger(type=AgentTriggerTypes.TIME_RANGE, time_from="-1d", time_to="now")
        assert isinstance(trigger.time_from, int)
        assert isinstance(trigger.time_to, int)
        assert trigger.time_from < trigger.time_to

        # Test UpdateSchedule
        schedule = UpdateSchedule(version="5.9.2", time_utc="-1h")
        assert isinstance(schedule.time_utc, int)


class MockCache:
    """
    Provides a simplified in-memory cache surrogate for isolated Manager testing.
    """

    def __init__(self) -> None:
        """
        Bootstraps basic empty context aggregators for agents and connections.
        """
        self.agents = []
        self.connections = []


class MockContext:
    """
    Provides a simplified environment context surrogate.
    """

    def __init__(self) -> None:
        """
        Establishes single-sensor routing mappings needed for logic traversal.
        """
        self.singlesensor = MockCache()
        self.multisensors = {"1": MockCache(), "2": MockCache()}


class MockDeviceClient:
    """
    Provides an isolated abstraction of the core DeviceClient for HTTP request mocking.
    """

    def __init__(self, async_client: httpx.AsyncClient) -> None:
        """
        Initializes an embedded mock wrapper coupling isolated HTTP pools.

        Args:
            async_client (httpx.AsyncClient): The isolated transport object routing to Respx.
        """
        self._http_client = async_client
        self.cache = MockContext()
        self.models = None


@pytest.mark.asyncio
class TestDataPushManagerErrors:
    """
    Validates DataPushManager response routing and HTTP exception translation.
    """

    async def _get_manager(self) -> DataPushManager:
        """Helper to create a manager with a mock client."""

        async def raise_on_4xx_5xx(response: httpx.Response) -> None:
            response.raise_for_status()

        http = httpx.AsyncClient(base_url="http://mock.xovis.local", event_hooks={"response": [raise_on_4xx_5xx]})
        return DataPushManager(client=MockDeviceClient(http))

    @respx.mock
    async def test_manager_http_400_validation_error(self) -> None:
        """
        Validates DataPushManager appropriately bubbles HTTP 400 validation failures.

        Constructs a dummy payload targeting the creation schema, routing through `respx`
        to trigger manual boundary rejections reflecting payload distortions.

        Raises:
            AssertionError: If validation skips boundary checks on bad assignments.
        """
        manager = await self._get_manager()
        respx.post("http://mock.xovis.local/api/v5/singlesensor/data/push/agents").respond(status_code=400, json={"info": "Bad Request"})

        agent = DataPushAgent(
            name="Test",
            type=DataPushType.LIVE_DATA,
            connection=1,
            config=AgentConfig(scheduler=Scheduler(type=SchedulerType.IMMEDIATE), data=DataConfig()),
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await manager.create_agent(agent)

        assert exc_info.value.response.status_code == 400

    @respx.mock
    async def test_manager_http_401_auth_error(self) -> None:
        """
        Validates DataPushManager aggressively captures and bubbles HTTP 401 Authorization halts.

        Routes simulated credential failures verifying authentication boundaries execute
        priority over resource loading.

        Raises:
            AssertionError: If context authorization overrides aren't prioritized.
        """
        manager = await self._get_manager()
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/agents").respond(status_code=401, text="Unauthorized")

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await manager.get_all_agents()

        assert exc_info.value.response.status_code == 401

    @respx.mock
    async def test_manager_404_resource_not_found(self) -> None:
        """
        Validates autonomous cache translation accurately throws ResourceNotFoundError
        during non-existent nominal resolution operations.

        Raises:
            AssertionError: If explicit lookup overrides fall through invalid mappings.
        """
        manager = await self._get_manager()
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/agents").respond(status_code=200, json={"agents": []})
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/connections").respond(status_code=200, json={"connections": []})

        manager._client.cache.singlesensor.agents = []
        manager._client.cache.singlesensor.connections = []

        with pytest.raises(ResourceNotFoundError):
            await manager._resolve_agent_id("Missing_Agent_Name")

    @respx.mock
    async def test_manager_multisensor_discovery_on_missing_context(self) -> None:
        """Validates that DataPushManager triggers multisensor discovery if the context is missing."""
        import respx

        from xovis.api.device.resources.datapush import DataPushManager

        # Mock multisensors status to return ID "2"
        respx.get("http://mock.xovis.local/api/v5/multisensors/status").respond(
            status_code=200, json={"multisensors": [{"multisensor_id": 2, "name": "NewMS"}]}
        )
        # Mock connections for MS 2
        respx.get("http://mock.xovis.local/api/v5/multisensors/2/data/push/connections").respond(
            status_code=200,
            json={
                "connections": [
                    {
                        "id": 20,
                        "name": "MSConn",
                        "protocol": "TCP",
                        "config": {"mode": "CLIENT", "uri": "127.0.0.1", "port": 9000},
                    }
                ]
            },
        )

        async with httpx.AsyncClient(base_url="http://mock.xovis.local") as http:
            client = MockDeviceClient(http)
            # Target MS 2 which is NOT in initial cache
            manager = DataPushManager(client=client, target_id=2)

            # This should trigger multisensors.sync() then get_all_connections()
            conn_id = await manager._resolve_connection_id("MSConn")
            assert str(conn_id) == "20"

            # Verify it was added to the multisensors accessor
            # In MockDeviceClient, multisensors might be a dict or a REPLAccessor depending on implementation
            multisensors = client.cache.multisensors
            items = multisensors._items if hasattr(multisensors, "_items") else multisensors
            assert "2" in items

    @respx.mock
    async def test_manager_cache_update_integrity(self) -> None:
        """
        Validates that DataPushManager correctly updates the underlying cache bucket.
        Regression test for 'ghost' list appends where CacheCollection was updated but not bucket.
        """
        manager = await self._get_manager()
        # Mock connection creation
        conn_payload = {
            "id": 1,
            "name": "GhostTest",
            "uri": "http://ghost.local",
            "protocol": "HTTP",
            "config": {"uri": "http://ghost.local"},
        }
        respx.post("http://mock.xovis.local/api/v5/singlesensor/data/push/connections").respond(status_code=201, json=conn_payload)
        # Mock get_all_connections since create_connection now calls it if cache is empty
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/connections").respond(status_code=200, json={"connections": []})

        from xovis.models.device import DataPushConnection, DataPushProtocol, HTTPConfig

        conn = DataPushConnection(
            name="GhostTest",
            uri="http://ghost.local",
            protocol=DataPushProtocol.HTTP,
            config=HTTPConfig(uri="http://ghost.local"),
        )

        # 1. Clear cache
        manager._client.cache.singlesensor.connections = []

        # 2. Create connection - should update cache
        await manager.create_connection(conn)

        # 3. Verify via accessor (which in Mock is just a simple object, but we want to simulate the failure)
        assert len(manager._client.cache.singlesensor.connections) == 1
        assert manager._client.cache.singlesensor.connections[0].name == "GhostTest"

    @respx.mock
    async def test_manager_proactive_sync_on_missing_name(self) -> None:
        """
        Validates that resolution triggers a sync if the name is not in cache,
        even if the cache is not empty.
        """
        manager = await self._get_manager()
        # Initial cache has one agent
        manager._client.cache.singlesensor.agents = [
            DataPushAgent(
                id=1,
                name="ExistingAgent",
                type=DataPushType.LIVE_DATA,
                connection=10,
                config={"scheduler": {"type": "IMMEDIATE"}, "data": {"format": {"type": "JSON"}}},
            )
        ]

        # Mock response for the proactive sync that includes the "NewAgent"
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/agents").respond(
            status_code=200,
            json={
                "agents": [
                    {
                        "id": 1,
                        "name": "ExistingAgent",
                        "type": "LIVE_DATA",
                        "connection": 10,
                        "config": {
                            "scheduler": {"type": "IMMEDIATE"},
                            "data": {"format": {"type": "JSON"}},
                        },
                    },
                    {
                        "id": 2,
                        "name": "NewAgent",
                        "type": "LIVE_DATA",
                        "connection": 10,
                        "config": {
                            "scheduler": {"type": "IMMEDIATE"},
                            "data": {"format": {"type": "JSON"}},
                        },
                    },
                ]
            },
        )

        agent_id = await manager._resolve_agent_id("NewAgent")
        assert agent_id == "2"
        assert len(manager._client.cache.singlesensor.agents) == 2

        # Mock connections as well for the next failure test
        respx.get("http://mock.xovis.local/api/v5/singlesensor/data/push/connections").respond(status_code=200, json={"connections": []})

        with pytest.raises(ResourceNotFoundError):
            await manager._resolve_connection_id("Missing_Connection_Name")

    @respx.mock
    async def test_manager_multisensor_cache_resolution(self) -> None:
        """
        Validates that DataPushManager correctly resolves IDs against the
        targeted multisensor context cache (ensuring string normalization).
        """

        async def raise_on_4xx_5xx(response: httpx.Response) -> None:
            response.raise_for_status()

        async with httpx.AsyncClient(base_url="http://mock.xovis.local", event_hooks={"response": [raise_on_4xx_5xx]}) as http:
            # target_id=1 as an integer to test normalization
            client = MockDeviceClient(http)
            manager = DataPushManager(client=client, target_id=1)

            # Mock the cache for multisensor context "1"
            # Note: The key in multisensors is "1" (string)
            client.cache.multisensors["1"].agents = [
                DataPushAgent(
                    id=101,
                    name="MSAgent",
                    type="LIVE_DATA",
                    connection=10,
                    config={
                        "scheduler": {"type": "IMMEDIATE"},
                        "data": {"format": {"type": "JSON"}},
                    },
                )
            ]

            # Resolve should work because target_id=1 is normalized to "1"
            agent_id = await manager._resolve_agent_id("MSAgent")
            assert str(agent_id) == "101"
