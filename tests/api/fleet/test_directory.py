"""
Stateless tests for HubFleetDirectory parsing and autosuggestions.
"""

from pathlib import Path

import pytest

from xovis.api.fleet.directory import HubFleetDirectory


def test_hub_fleet_directory_from_raw():
    devices = [
        {"id": "00:11:22:33:44:55", "ip": "10.0.0.1", "device_name": "Entrance 1", "categories": ["Retail"], "customer": "CustA"},
        {"id": "00:11:22:33:44:66", "ip": "10.0.0.2", "device_name": "Checkout 1", "categories": ["Retail", "Office"], "customer": "CustA"},
    ]
    directory = HubFleetDirectory(devices)

    # Test sanitization and indexing
    assert "Entrance_1" in dir(directory.by_name)
    assert "Checkout_1" in dir(directory.by_name)

    # Test retrieval
    assert directory.by_name.Entrance_1["ip"] == "10.0.0.1"

    # Test grouping
    assert len(directory.by_customer.CustA) == 2
    assert len(directory.by_category.Retail) == 2
    assert len(directory.by_category.Office) == 1
    assert directory.by_category.Office[0]["ip"] == "10.0.0.2"


def test_hub_fleet_directory_from_file(tmp_path: Path):
    file_path = tmp_path / "test_hub_state.json"
    file_path.write_text('{"devices": [{"id": "mac1", "device_name": "Sensor A"}]}', encoding="utf-8")

    directory = HubFleetDirectory.from_file(file_path)
    assert "Sensor_A" in dir(directory.by_name)
    assert directory.by_name.Sensor_A["id"] == "mac1"
