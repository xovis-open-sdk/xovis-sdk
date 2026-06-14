import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to sys.path to find examples and src
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))


# Mocking the network calls to avoid actual connections
class TestExamples(unittest.IsolatedAsyncioTestCase):
    @patch("xovis.api.core.http.httpx.AsyncClient.request")
    async def test_example_01_logic(self, mock_request):
        # Mock responses for 01_edge_basics.py
        mock_request.side_effect = self.mock_sensor_responses

        import importlib

        example_01 = importlib.import_module("examples.01_edge_basics")
        example_main = example_01.main

        # Set environment variables expected by the example
        os.environ["XOVIS_SENSOR_HOST"] = "10.0.0.50"
        os.environ["XOVIS_SENSOR_PASS"] = "password"

        # We need to mock the context manager and internals because main() runs everything
        # Actually, let's just run it and see where it fails if the mocks aren't enough.
        try:
            await asyncio.wait_for(example_main(), timeout=5.0)
        except Exception as e:
            self.fail(f"Example 01 failed: {e}")

    @patch("xovis.api.core.http.httpx.AsyncClient.request")
    async def test_example_03_logic(self, mock_request):
        mock_request.side_effect = self.mock_sensor_responses

        import importlib

        example_03 = importlib.import_module("examples.03_topology_and_state")
        example_main = example_03.main

        os.environ["XOVIS_SENSOR_HOST"] = "10.0.0.50"
        os.environ["XOVIS_SENSOR_USER"] = "admin"
        os.environ["XOVIS_SENSOR_PASS"] = "password"

        try:
            await asyncio.wait_for(example_main(), timeout=5.0)
        except Exception as e:
            self.fail(f"Example 03 failed: {e}")

    def mock_sensor_responses(self, method, url, **kwargs):
        url_str = str(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        if "/api/v5/config/state" in url_str:
            mock_resp.json.return_value = {"state": {"checksum": "123"}}
        elif "/api/v5/singlesensor/info" in url_str:
            mock_resp.json.return_value = {"type": "PC2S", "fw_version": "5.9.11"}
        elif "/api/v5/singlesensor/analytics/logics" in url_str:
            if method == "GET" and "Store%20Entrance" in url_str:
                mock_resp.json.return_value = {"id": 1, "name": "Store Entrance"}
            else:
                mock_resp.json.return_value = [{"id": 1, "name": "Store Entrance"}]
        elif "/api/v5/singlesensor/data/history/logics" in url_str:
            mock_resp.json.return_value = {"bins": []}
        elif "/api/v5/multisensors/status" in url_str:
            mock_resp.json.return_value = {"multisensors_status": [{"id": 1, "name": "Main Entrance", "master": "AA:BB:CC:DD:EE:FF"}]}
        elif "/api/v5/discover/localnetwork" in url_str:
            mock_resp.json.return_value = {"sensors": [{"mac": "AA:BB:CC:DD:EE:FF", "ip": "10.0.0.50"}]}
        elif "/api/v5/multisensors/1/sensors" in url_str:
            mock_resp.json.return_value = {"sensors": []}
        elif "/api/v5/multisensors/1/scene/geometries" in url_str:
            mock_resp.json.return_value = {"zones": [], "lines": []}
        else:
            mock_resp.json.return_value = {}

        return mock_resp


if __name__ == "__main__":
    unittest.main()
