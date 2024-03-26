#!/usr/local/bin/python3
# coding=utf-8
"""
This module defines classes for discovering IoT devices using MQTT.

Classes:
    Device: Represents a device with address, friendly name, model, and protocol.
    Discoverer: Discovers devices using MQTT.
    ZigbeeDiscoverer: Discovers Zigbee devices using MQTT.
    TasmotaDiscoverer: Discovers Tasmota devices using MQTT.

Discoverer is the base class for device discovery. It uses an MQTT client 
to discover devices and maintains a list of discovered devices. It also 
allows adding discovery processors for processing the discovered devices.

ZigbeeDiscoverer and TasmotaDiscoverer are subclasses of Discoverer. They 
override the base class methods to provide specific implementations for 
discovering Zigbee and Tasmota devices, respectively.

Device class provides properties for accessing these attributes and methods 
for getting string representations of the device.
"""
import json

from iotlib.utils import iotlib_logger
from iotlib.abstracts import DiscoveryProcessor
from iotlib.client import MQTTClient
from iotlib.codec.config import BaseTopic
from iotlib.factory import Model, Protocol


class Device():
    """Represents a device with an address, friendly name, model, and protocol."""
    def __init__(self,
                 address: str,
                 friendly_name: str,
                 model: Model,
                 protocol: Protocol):
        self._address = address
        self._friendly_name = friendly_name
        self._model = model
        self._protocol = protocol

    @property
    def address(self) -> str:
        """Returns the address of the device."""
        return self._address

    @property
    def friendly_name(self) -> str:
        """Returns the friendly name of the device."""
        return self._friendly_name

    @property
    def model(self) -> Model:
        """Returns the model of the device."""
        return self._model

    @property
    def protocol(self) -> Protocol:
        """Returns the protocol of the device."""
        return self._protocol


    def __str__(self):
        """Returns a string representation of the device."""
        return f"<{self.__class__.__name__} : {self.friendly_name}>"

    def __repr__(self):
        """Returns a developer-friendly representation of the device."""
        return f"<{self.__class__.__name__} : {self.friendly_name}, address : {self.address}, model: {self.model}, protocol: {self.protocol}>"

class Discoverer():
    """Discovers devices."""
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt_client = mqtt_client
        self.devices = []
        self._discovery_processors = []

    def get_devices(self) -> list[Device]:
        return self.devices

    def add_discovery_processor(self, processor: DiscoveryProcessor) -> None:
        """Appends an Discovery Processor instance to the processor list
        """
        if not isinstance(processor, DiscoveryProcessor):
            _msg = f"Processor must be instance of DiscoveryProcessor, not {type(processor)}"
            raise TypeError(_msg)
        self._discovery_processors.append(processor)


class ZigbeeDiscoverer(Discoverer):
    def __init__(self, mqtt_client: MQTTClient):
        """Initializes the ZigbeeDiscoverer with the given MQTT client."""
        super().__init__(mqtt_client)
        self._base_topic = BaseTopic.Z2M_BASE_TOPIC.value + '/bridge/devices'
        self.mqtt_client.message_callback_add(self._base_topic,
                                              self._on_message_cb)
        self.mqtt_client.connect_handler_add(self._on_connect_cb)

    def _on_message_cb(self, client, userdata, message) -> None:
        """Handles incoming MQTT messages."""
        payload = str(message.payload.decode("utf-8"))
        _new_devices = self._parse_devices(json.loads(payload))
        for _processor in self._discovery_processors:
            _processor.process_discovery_update(_new_devices)

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Handles the MQTT connection event."""
        iotlib_logger.debug(
            '[%s] Connection accepted -> subscribe', self.mqtt_client)
        self.mqtt_client.subscribe(self._base_topic)

    def _parse_devices(self, payload: json) -> list[Device]:
            """
            Parses the devices from the given payload.

            Args:
                payload (json): The payload containing the device information.

            Returns:
                List[Device]: The list of newly discovered devices.
            """
            devices = [Device(entry.get("ieee_address"),
                                   entry.get("friendly_name"),
                                   Model.from_str(entry.get("definition", {}).get("model")),
                                   Protocol.Z2M)
                            for entry in payload if entry.get("type") == 'EndDevice']
            self.devices.append(devices)

            return devices


class TasmotaDiscoverer(Discoverer):
    """Discovers Tasmota devices using MQTT."""
    def __init__(self, mqtt_client: MQTTClient):
        super().__init__(mqtt_client)
        self.devices = []
        self._base_topic = BaseTopic.TASMOTA_DISCOVERY_TOPIC.value + '/+/config'
        self.mqtt_client.message_callback_add(self._base_topic,
                                              self._on_message_cb)
        self.mqtt_client.connect_handler_add(self._on_connect_cb)

    def _on_message_cb(self, client, userdata, message) -> None:
        """Handles incoming MQTT messages."""
        payload = str(message.payload.decode("utf-8"))
        new_devices = self._parse_devices(payload=json.loads(payload))
        for _processor in self._discovery_processors:
            _processor.process_discovery_update(new_devices)

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Handles the MQTT connection event."""
        iotlib_logger.debug(
            '[%s] Connection accepted -> subscribe', self.mqtt_client)
        self.mqtt_client.subscribe(self._base_topic)

    def _parse_devices(self, payload: dict) -> list[Device]:
        """Parses the devices from the given payload."""
        if all (k in payload for k in ("hn", "t", "md")):
            device = Device(payload.get("hn"),
                            payload.get("t"),
                            Model.from_str(payload.get('md')),
                            Protocol.TASMOTA)
            self.devices.append(device)
            return [device]


class UnifiedDiscoverer():
    """
    A class that unifies the discovery of devices from different protocols.
    """
    def __init__(self, mqtt_client: MQTTClient):
        """
        Initializes the UnifiedDiscoverer with a list of specific protocol discoverers.
        """
        self._discoverers = [ZigbeeDiscoverer(mqtt_client), TasmotaDiscoverer(mqtt_client)]

    def get_devices(self) -> list[Device]:
        """
        Returns a list of all devices discovered by all protocol discoverers.
        """
        return [device for _discoverer in self._discoverers for device in _discoverer.get_devices()]

    def add_discovery_processor(self, processor: DiscoveryProcessor) -> None:
        """Appends an Discovery Processor instance to the processor list
        """
        for _discoverer in self._discoverers:
            _discoverer.add_discovery_processor(processor)
