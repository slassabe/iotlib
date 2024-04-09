#!/usr/local/bin/python3
# coding=utf-8
"""
This module defines classes for discovering IoT devices using MQTT.

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
from iotlib.abstracts import IDiscoveryProcessor, IMQTTService
from iotlib.codec.config import BaseTopic
from iotlib.factory import Model, Protocol


class Device():
    """
    Represents a generic device in the system.

    This class provides a base for all types of devices. It defines common properties and methods 
    that all devices should have. Specific device types should inherit from this class and add 
    their own unique properties and methods.

    :ivar id: The unique identifier for the device.
    :vartype id: str
    :ivar name: The human-readable name of the device.
    :vartype name: str
    :ivar type: The type of the device (e.g., 'sensor', 'actuator').
    :vartype type: str
    :ivar status: The current status of the device (e.g., 'online', 'offline').
    :vartype status: str
    """
    def __init__(self,
                 address: str,
                 friendly_name: str,
                 model: Model,
                 protocol: Protocol):
        """
        Initializes a new instance of the Discoverer class.

        :param address: The IP address or hostname of the device.
        :type address: str
        :param friendly_name: The friendly name of the device.
        :type friendly_name: str
        :param model: The model of the device.
        :type model: Model
        :param protocol: The protocol used by the device.
        :type protocol: Protocol
        """
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
        return f"<{self.__class__.__name__} : {self.friendly_name}>"

    def __repr__(self):
        return f"<{self.__class__.__name__} : {self.friendly_name}, address : {self.address}, model: {self.model}, protocol: {self.protocol}>"


class Discoverer():
    """
    Discovers devices on the network.

    This class provides methods to discover devices on the network using different protocols. 
    It can be used to find devices, get their information, and add them to the system.

    :ivar address: The IP address or hostname of the device.
    :vartype address: str
    :ivar friendly_name: The friendly name of the device.
    :vartype friendly_name: str
    :ivar model: The model of the device.
    :vartype model: Model
    :ivar protocol: The protocol used by the device.
    :vartype protocol: Protocol
    """
    def __init__(self, mqtt_service: IMQTTService):
        """
        Initializes a new instance of the Discoverer class.

        :param mqtt_service: The MQTT service to be used for device discovery.
        :type mqtt_service: IMQTTService
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be an instance of MQTTService, not {type(mqtt_service)}")
        self.mqtt_service = mqtt_service
        self.devices = []
        self._discovery_processors = []

    def get_devices(self) -> list[Device]:
        """
        Gets the list of discovered devices.

        This method returns the list of Device objects that have been discovered by the Discoverer.

        :return: A list of Device objects.
        :rtype: list[Device]
        """
        return self.devices

    def add_discovery_processor(self, processor: IDiscoveryProcessor) -> None:
        """
        Adds a discovery processor to the Discoverer.

        Discovery processors are used to process the results of a device discovery operation. 
        This method allows adding custom processors to the Discoverer.

        :param processor: The discovery processor to be added.
        :type processor: IDiscoveryProcessor
        """
        if not isinstance(processor, IDiscoveryProcessor):
            _msg = f"Processor must be instance of DiscoveryProcessor, not {type(processor)}"
            raise TypeError(_msg)
        self._discovery_processors.append(processor)


class ZigbeeDiscoverer(Discoverer):
    """
    Discovers Zigbee devices on the network.

    This class extends the Discoverer class and provides methods to discover Zigbee 
    devices on the network. 
    It uses the Zigbee protocol for device discovery.

    :ivar address: The IP address or hostname of the Zigbee device.
    :vartype address: str
    :ivar friendly_name: The friendly name of the Zigbee device.
    :vartype friendly_name: str
    :ivar model: The model of the Zigbee device.
    :vartype model: Model
    :ivar protocol: The protocol used by the Zigbee device, should be Zigbee.
    :vartype protocol: Protocol
    """
    def __init__(self, mqtt_service: IMQTTService):
        """Initializes the ZigbeeDiscoverer with the given MQTT client."""
        super().__init__(mqtt_service)
        self._base_topic = BaseTopic.Z2M_BASE_TOPIC.value + '/bridge/devices'
        mqtt_service.mqtt_client.message_callback_add(self._base_topic,
                                                      self._on_message_cb)
        mqtt_service.connect_handler_add(self._on_connect_cb)

    def _on_message_cb(self, client, userdata, message) -> None:
        """Handles incoming MQTT messages."""
        payload = str(message.payload.decode("utf-8"))
        _new_devices = self._parse_devices(json.loads(payload))
        for _processor in self._discovery_processors:
            _processor.process_discovery_update(_new_devices)

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Handles the MQTT connection event."""
        iotlib_logger.debug(
            '[%s] Connection accepted -> subscribe', self.mqtt_service)
        self.mqtt_service.mqtt_client.subscribe(self._base_topic)

    def _parse_devices(self, payload: json) -> list[Device]:
        """
        Parses the payload to extract device information.

        This method takes a JSON payload, typically received from a device discovery operation, 
        and extracts device information from it. It returns a list of Device objects.

        :param payload: The JSON payload to parse.
        :type payload: json
        :return: A list of Device objects extracted from the payload.
        :rtype: list[Device]
        """
        devices = [Device(entry.get("ieee_address"),
                          entry.get("friendly_name"),
                          Model.from_str(
                              entry.get("definition", {}).get("model")),
                          Protocol.Z2M)
                   for entry in payload if entry.get("type") == 'EndDevice']
        self.devices = devices

        return devices


class TasmotaDiscoverer(Discoverer):
    """
    Discovers Tasmota devices on the network.

    This class extends the Discoverer class and provides methods to discover Tasmota 
    devices on the network. It uses the Tasmota protocol for device discovery.

    :ivar address: The IP address or hostname of the Tasmota device.
    :vartype address: str
    :ivar friendly_name: The friendly name of the Tasmota device.
    :vartype friendly_name: str
    :ivar model: The model of the Tasmota device.
    :vartype model: Model
    :ivar protocol: The protocol used by the Tasmota device, should be Tasmota.
    :vartype protocol: Protocol
    """
    def __init__(self, mqtt_service: IMQTTService):
        super().__init__(mqtt_service)
        self.devices = []
        self._base_topic = BaseTopic.TASMOTA_DISCOVERY_TOPIC.value + '/+/config'
        mqtt_service.mqtt_client.message_callback_add(self._base_topic,
                                                      self._on_message_cb)
        mqtt_service.connect_handler_add(self._on_connect_cb)

    def _on_message_cb(self, client, userdata, message) -> None:
        """Handles incoming MQTT messages."""
        payload = str(message.payload.decode("utf-8"))
        new_devices = self._parse_devices(payload=json.loads(payload))
        for _processor in self._discovery_processors:
            _processor.process_discovery_update(new_devices)

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Handles the MQTT connection event."""
        iotlib_logger.debug(
            '[%s] Connection accepted -> subscribe', self.mqtt_service)
        self.mqtt_service.mqtt_client.subscribe(self._base_topic)

    def _parse_devices(self, payload: dict) -> list[Device]:
        """Parses the devices from the given payload."""
        if all(k in payload for k in ("hn", "t", "md")):
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

    def __init__(self, mqtt_service: IMQTTService):
        """ Initializes the UnifiedDiscoverer with a list of specific protocol discoverers.
        """
        self._discoverers = [ZigbeeDiscoverer(
            mqtt_service), TasmotaDiscoverer(mqtt_service)]

    def get_devices(self) -> list[Device]:
        """ Returns a list of all devices discovered by all protocol discoverers.
        """
        return [device for _discoverer in self._discoverers for device in _discoverer.get_devices()]

    def add_discovery_processor(self, processor: IDiscoveryProcessor) -> None:
        """Appends an Discovery Processor instance to the processor list
        """
        for _discoverer in self._discoverers:
            _discoverer.add_discovery_processor(processor)
