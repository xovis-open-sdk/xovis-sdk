"""
Xovis SDK - Image Management Resource

Provides the implementation for retrieving background, raw lens, stereo,
and depth images from local edge sensors.
"""

import json
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from xovis.api.device.client import DeviceClient


class ImagesManager:
    """
    Manages image retrieval for the single-sensor context.
    """

    def __init__(self, client: "DeviceClient", target_id: Optional[str] = None) -> None:
        """
        Initializes the ImagesManager.

        Args:
            client (DeviceClient): The parent device client instance.
            target_id (Optional[str]): The multisensor target ID, if applicable.
        """
        self._client = client
        self._http = client._http_client
        self.target_id = target_id

    def _resolve_path(self, perspective: str = "scene") -> str:
        """Resolves the base path for images."""
        if self.target_id:
            return f"/api/v5/multisensors/{self.target_id}/{perspective}/images"
        return f"/api/v5/singlesensor/{perspective}/images"

    async def get_raw_left(self) -> bytes:
        """
        Fetches the raw left lens image.

        Returns:
            bytes: The raw JPEG image binary data.
        """
        if self.target_id:
            # Spiders don't have raw lenses in multisensor context usually,
            # but we'll follow the pattern if possible.
            # Actually, raw_left is usually only at root.
            pass
        response = await self._http.get("/api/v5/singlesensor/images/raw_left.jpg")
        return response.content

    async def get_raw_right(self) -> bytes:
        """
        Fetches the raw right lens image.

        Returns:
            bytes: The raw JPEG image binary data.
        """
        response = await self._http.get("/api/v5/singlesensor/images/raw_right.jpg")
        return response.content

    async def get_stereo(self) -> bytes:
        """
        Fetches the stereo image.

        Returns:
            bytes: The PNG image binary data.
        """
        response = await self._http.get("/api/v5/singlesensor/images/stereo.png")
        return response.content

    async def get_depth_map(self, colored: bool = False) -> bytes:
        """
        Fetches the depth map image.

        Args:
            colored (bool): If True, requests the colored depth map.
                Defaults to False.

        Returns:
            bytes: The depth map PNG binary data.
        """
        endpoint = (
            "/api/v5/singlesensor/experimental/view/images/depth_color.png" if colored else "/api/v5/singlesensor/experimental/view/images/depth.png"
        )
        response = await self._http.get(endpoint)
        return response.content

    async def get_background(self, perspective: str = "scene") -> tuple[bytes, dict[str, Any]]:
        """
        Fetches the static background image.

        Args:
            perspective (str): The coordinate projection to use ("scene" or "view").
                Defaults to "scene".

        Returns:
            Tuple[bytes, Dict[str, Any]]: A tuple containing the JPEG binary data
                and a dictionary of the parsed image metadata.
        """
        response = await self._http.get(f"{self._resolve_path(perspective)}/background.jpg")
        metadata = json.loads(response.headers.get("x-image-metadata", "{}"))
        return response.content, metadata

    async def get_background_tarball(
        self,
        perspective: str = "scene",
        json_int64_workaround: bool = False,
        tracked_objects: bool = True,
        events: bool = True,
    ) -> bytes:
        """
        Fetches the static background image and metadata as a raw tarball.

        Args:
            perspective (str): The coordinate projection to use ("scene" or "view"). Defaults to "scene".
            json_int64_workaround (bool): Include workaround for 64-bit JSON ints. Defaults to False.
            tracked_objects (bool): Include tracked objects overlay data. Defaults to True.
            events (bool): Include events overlay data. Defaults to True.

        Returns:
            bytes: The raw tarball binary data containing 'image.jpg' and 'X-Image-Metadata.json'.
        """
        params = {
            "json_int64_workaround": str(json_int64_workaround).lower(),
            "tracked_objects": str(tracked_objects).lower(),
            "events": str(events).lower(),
        }
        headers = {"accept": "application/x-tar"}
        response = await self._http.get(f"{self._resolve_path(perspective)}/background.tar", params=params, headers=headers)
        return response.content

    async def get_live(self, perspective: str = "scene") -> tuple[bytes, dict[str, Any]]:
        """
        Fetches the live image.

        Args:
            perspective (str): The coordinate projection to use ("scene" or "view").
                Defaults to "scene".

        Returns:
            Tuple[bytes, Dict[str, Any]]: A tuple containing the JPEG binary data
                and a dictionary of the parsed image metadata.
        """
        response = await self._http.get(f"{self._resolve_path(perspective)}/live.jpg")
        metadata = json.loads(response.headers.get("x-image-metadata", "{}"))
        return response.content, metadata

    async def reset_background(self, perspective: str = "scene") -> None:
        """
        Resets the background image.

        Args:
            perspective (str): The projection context to reset. Defaults to "scene".
        """
        await self._http.post(f"{self._resolve_path(perspective)}/background/reset")

    async def update_settings_image(self) -> None:
        """
        Updates the settings image used for configuration.
        """
        await self._http.post("/api/v5/singlesensor/settings/image/update")
