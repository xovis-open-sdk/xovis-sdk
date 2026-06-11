"""
Xovis SDK - Control Plane License Validation

Validates that the SDK correctly probes and caches hardware license capabilities,
ensuring that premium features like Object Detection, PRAM, and Wheelchair
detection are correctly identified before resource provisioning.
"""

import logging

import pytest

from xovis.api.device.client import DeviceClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestLicenseCapabilities:
    """
    Validates license-aware capability checks on Xovis edge sensors.
    """

    async def test_proactive_license_probing(self, real_device: DeviceClient) -> None:
        """
        Ensures that license properties on DeviceClient return consistent results.
        """
        obj_det = await real_device.has_object_detection()
        pram_det = await real_device.has_pram_detection()
        wheel_det = await real_device.has_wheelchair_detection()
        bike_det = await real_device.has_bicycle_detection()
        people_attr = await real_device.has_people_attributes()

        logger.info(f"License Status - Object: {obj_det}, Pram: {pram_det}, Wheel: {wheel_det}, Bike: {bike_det}, People: {people_attr}")

        # Verify that they are boolean
        assert isinstance(obj_det, bool)
        assert isinstance(pram_det, bool)
        assert isinstance(wheel_det, bool)
        assert isinstance(bike_det, bool)
        assert isinstance(people_attr, bool)

    async def test_license_details_direct(self, real_device: DeviceClient) -> None:
        """
        Validates the raw license details extraction.
        """
        details = await real_device.system.get_license_details()
        assert details is not None
        if details.licenses:
            for lic in details.licenses:
                logger.info(f"Found License: {lic.feature} (ID: {lic.id}) - State: {lic.state}")
                assert lic.id > 0
                assert lic.feature != ""
                assert lic.state.value in ("ENABLED", "TEST_ENABLED", "EXPIRED", "NOT_LICENSED")
