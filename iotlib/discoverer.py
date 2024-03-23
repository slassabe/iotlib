#!/usr/local/bin/python3
# coding=utf-8

import time
import logging
import json
from iotlib.client import MQTTClient
from iotlib.factory import Model, Protocol
from iotlib.abstracts import DiscoveryProcessor
from iotlib import package_level_logger


class Device():
    def __init__(self,
                 address: str,
                 friendly_name: str, 
                 model: Model, 
                 protocol: Protocol):
        self.address = address
        self.friendly_name = friendly_name
        self.model = model
        self.protocol = protocol

    def __str__(self):
        return f"<{self.__class__.__name__} : {self.friendly_name}, address : {self.address}, model: {self.model}, protocol: {self.protocol}>"

    def __repr__(self):
        return f"<{self.__class__.__name__} : {self.friendly_name}>"


class Discoverer():
    _logger = package_level_logger
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt_client = mqtt_client
        self.devices = None
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
        super().__init__(mqtt_client)
        self.mqtt_client.message_callback_add('zigbee2mqtt/bridge/devices',
                                              self.on_message_cb)
        self.mqtt_client.connect_handler_add(self.on_connect_cb)
        #mqtt_client.start()

    def on_message_cb(self, client, userdata, message) -> None:
        """Handles incoming MQTT messages."""
        payload = str(message.payload.decode("utf-8"))
        self.devices = self._parse_devices(json.loads(payload))
        for _processor in self._discovery_processors:
            _processor.process_discovery_update(self.devices)

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Handles the MQTT connection event."""
        self._logger.debug('[%s] Connection accepted -> subscribe', self.mqtt_client)
        self.mqtt_client.subscribe('zigbee2mqtt/bridge/devices')

    @staticmethod
    def _parse_devices(payload: json) -> list[Device]:
        """Parses the devices from the given payload."""
        devices = []
        for entry in payload:
            _ieee_address = entry.get("ieee_address")
            _friendly_name = entry.get("friendly_name")
            _type = entry.get("type")
            _definition = entry.get("definition")
            if _definition:
                _model = _definition.get("model")
                _vendor = _definition.get("vendor")
            else:
                _model = None
                _vendor = None
            if _type == 'EndDevice':
                devices.append(Device(_ieee_address,
                                      _friendly_name,
                                      Model.from_str(_model),
                                      Protocol.Z2M))
        return devices
