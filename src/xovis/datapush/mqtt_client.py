"""
Xovis SDK - Data Plane MQTT Client

This module implements a high-performance MQTT ingestion client for Xovis telemetry.
It utilizes `aiomqtt` to subscribe to broker topics, process JSON payloads, and
dispatch them to attached sinks while natively handling network backpressure.
"""

import asyncio
import logging
import ssl
from typing import Optional

import aiomqtt

from xovis.datapush.sinks import XovisSink
from xovis.datapush.utils import DataPlaneIngestor

logger = logging.getLogger("xovis_sdk.mqtt")


class XovisMQTTClient:
    """
    Active MQTT Ingestion Client for Xovis Telemetry.

    Connects to an MQTT broker, subscribes to the configured telemetry topic,
    and routes incoming JSON payloads to the attached sinks. Supports TLS
    and username/password authentication.
    """

    def __init__(
        self,
        host: str,
        topic: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
    ):
        """
        Initializes the XovisMQTTClient.

        Args:
            host (str): The IP address or hostname of the MQTT broker.
            topic (str): The MQTT topic to subscribe to.
            port (int, optional): The broker port. Defaults to 1883 (or 8883 if SSL is True).
            username (Optional[str], optional): Authentication username.
            password (Optional[str], optional): Authentication password.
            use_ssl (bool, optional): Whether to use TLS encryption. Defaults to False.
        """
        self.host = host
        self.port = 8883 if use_ssl and port == 1883 else port
        self.topic = topic
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.sinks: list[XovisSink] = []
        self._running = False

    def attach_sink(self, sink: XovisSink) -> "XovisMQTTClient":
        """
        Attaches a telemetry consumer to the client.

        Args:
            sink (XovisSink): An object implementing the XovisSink protocol.

        Returns:
            XovisMQTTClient: The client instance for method chaining.
        """
        self.sinks.append(sink)
        return self

    async def start(self) -> None:
        """
        Starts the MQTT client loop.

        Connects to the broker, subscribes to the topic, and listens for messages.
        `aiomqtt` automatically handles reconnections under the hood.
        """
        self._running = True

        tls_context = ssl.create_default_context() if self.use_ssl else None

        logger.info(f"Xovis MQTT Client connecting to {self.host}:{self.port} on topic '{self.topic}'")

        try:
            async with aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                tls_context=tls_context,
            ) as client:
                await client.subscribe(self.topic)
                logger.info(f"Successfully subscribed to {self.topic}")

                async for message in client.messages:
                    if not self._running:
                        break

                    try:
                        frame = DataPlaneIngestor.parse_frame(message.payload)
                        asyncio.create_task(DataPlaneIngestor.route_to_sinks(frame, self.sinks))

                    except Exception as e:
                        logger.error(f"Error processing MQTT message: {e}")

        except aiomqtt.MqttError as e:
            logger.error(f"MQTT connection error: {e}")
        except asyncio.CancelledError:
            logger.info("Xovis MQTT Client stopped")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Terminates the active connection loop."""
        self._running = False

