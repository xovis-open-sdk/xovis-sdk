"""
Xovis SDK - Validation Sink

Provides a thread-safe, headless telemetry interceptor for validating high-frequency
Data Plane streams during testing. Implements the XovisSink protocol and applies
strict concurrency locks for reliable E2E metric aggregation.
"""

import asyncio
import copy
import json
from typing import Any, Optional, Union

from xovis.datapush.sinks import XovisSink


class ValidationSink(XovisSink):
    """
    Stateful telemetry sink designed for high-frequency test assertions.
    """

    def __init__(self, agent_type: str = "LIVE_DATA", expected_mac: Optional[str] = None) -> None:
        """
        Initializes the validation sink.

        Args:
            agent_type (str): Expected telemetry envelope format.
            expected_mac (Optional[str]): Expected MAC address for Deep Payload Validation.
        """
        self.agent_type = agent_type
        self.expected_mac = expected_mac
        self.lock = asyncio.Lock()
        self.frame_received = asyncio.Event()
        self.total_frames = 0
        self.total_events = 0
        self.total_bytes = 0
        self.latest_frame: dict[str, Any] = {}
        self.events_breakdown: dict[str, int] = {}
        self.sequence_id = None

    async def on_frame(self, payload: Union[dict[str, Any], list[dict[str, Any]]]) -> None:
        """
        Ingests and validates raw telemetry envelopes with strict concurrency locking.

        Args:
            payload (Union[Dict[str, Any], List[Dict[str, Any]]]): Emitted telemetry payload.

        Raises:
            AssertionError: When sequence monotonic sequence is breached or MAC address does not align.
        """
        async with self.lock:
            # Avoid stringifying large binary blobs for byte counting
            if isinstance(payload, dict) and isinstance(payload.get("recording_data"), bytes):
                self.total_bytes += len(payload["recording_data"])
            else:
                self.total_bytes += len(json.dumps(payload))

            frames = payload if isinstance(payload, list) else [payload]

            for frame in frames:
                self.total_frames += 1
                self.latest_frame = copy.deepcopy(frame)

                # Skip deep validation for raw binary recording blocks
                if isinstance(frame.get("recording_data"), bytes):
                    continue

                pkg_info = frame.get("package_info", {})
                sensor_info = frame.get("sensor_info", {})

                if not pkg_info or not sensor_info:
                    data_block = (
                        frame.get("live_data")
                        or frame.get("logics_data")
                        or frame.get("status_data")
                        or frame.get("wifi_bt_data")
                        or frame.get("recording_data")
                    )
                    if isinstance(data_block, dict):
                        pkg_info = pkg_info or data_block.get("package_info", {})
                        sensor_info = sensor_info or data_block.get("sensor_info", {})

                if pkg_info:
                    current_seq = pkg_info.get("id")
                    if current_seq is not None:
                        if self.sequence_id is not None:
                            assert current_seq > self.sequence_id, f"Sequence ID monotonicity break: {current_seq} <= {self.sequence_id}"
                        self.sequence_id = current_seq

                if self.expected_mac and sensor_info:
                    mac = sensor_info.get("serial_number") or sensor_info.get("mac_address")
                    if mac:
                        norm_mac = mac.replace(":", "").replace("-", "").upper()
                        norm_expected = self.expected_mac.replace(":", "").replace("-", "").upper()
                        assert norm_mac == norm_expected, f"Hardware MAC mismatch: payload has {mac}, expected {self.expected_mac}"

                if self.agent_type == "LIVE_DATA":
                    live_data = frame.get("live_data", {})
                    for sf in live_data.get("frames", []):
                        for evt in sf.get("events", []):
                            evt_type = evt.get("type", "UNKNOWN")
                            self.events_breakdown[evt_type] = self.events_breakdown.get(evt_type, 0) + 1

                elif self.agent_type == "LOGICS":
                    logics_data = frame.get("logics_data", {})
                    records = logics_data.get("records", [])
                    for record in records:
                        for count in record.get("counts", []):
                            c_id = count.get("id") or count.get("counter_id")
                            if c_id is not None:
                                self.events_breakdown[f"LOGIC_{c_id}"] = self.events_breakdown.get(f"LOGIC_{c_id}", 0) + 1

            self.frame_received.set()

    async def on_events(self, events: list[Any]) -> None:
        """
        Aggregates supplementary standalone events.

        Args:
            events (List): Emitted standalone event lists.
        """
        async with self.lock:
            self.total_events += len(events)
