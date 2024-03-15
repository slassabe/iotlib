#!/usr/local/bin/python3
# coding=utf-8
from typing import Any
from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt

from iotlib import package_level_logger
from iotlib.abstracts import Surrogate, AvailabilityProcessor
from iotlib.client import MQTTClient
from iotlib.codec.core import AbstractCodec, DecodingException


class MQTTBridge(Surrogate):
    _logger = package_level_logger

    def __init__(self,
                 mqtt_client: MQTTClient,
                 codec: AbstractCodec):
        # self.client = mqtt_client
        # self.codec = codec
        super().__init__(mqtt_client, codec)

        self.availability: bool = None
        self._avail_proc_list: list[AvailabilityProcessor] = []

        # Set MQTT on_message callbacks
        self.client.message_callback_add(self.codec.get_availability_topic(),
                                         self._avalability_callback)
        for _topic_property in self.codec.get_subscription_topics():
            self.client.message_callback_add(_topic_property,
                                             self._property_callback)
        # Set MQTT connection handlers
        self.client.connect_handler_add(self._on_connect_callback)
        self.client.disconnect_handler_add(self._on_disconnect_callback)
        

    def __repr__(self) -> str:
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({_res})'

    def __str__(self) -> str:
        return f'{self.__class__.__name__} obj.'

    def is_available(self) -> bool:
        """ check if the device is available
        """
        return self.availability

    def avail_proc_append(self, processor: AvailabilityProcessor):
        """Appends an Availability Processor instance to the processor list
        """
        if not isinstance(processor, AvailabilityProcessor):
            _msg = f"Processor must be instance of AvailabilityProcessor, not {type(processor)}"
            raise TypeError(_msg)
        self._avail_proc_list.append(processor)

    def _avalability_callback(self,
                              client: mqtt.Client,
                              userdata: Any,
                              message: mqtt.MQTTMessage) -> None:
        payload = message.payload.decode("utf-8")
        try:
            self._handle_availability(payload)
        except DecodingException as exp:
            self._logger.exception('"[%s]" : Exception occured decoding : %s / %s',
                                   exp,
                                   message.topic,
                                   payload[:100])

    def _property_callback(self,
                           client: mqtt.Client,
                           userdata: Any,
                           message: mqtt.MQTTMessage) -> None:
        payload = message.payload.decode("utf-8")
        try:
            self._handle_values(message.topic, payload)
        except DecodingException as exp:
            self._logger.exception('"[%s]" : Exception occured decoding : %s / %s',
                                   exp,
                                   message.topic,
                                   payload[:100])

    def _on_connect_callback(self,
                             client: mqtt.Client,
                             userdata: Any,
                             flags: mqtt.ConnectFlags,
                             reason_code: mqtt.ReasonCode,
                             properties: mqtt.Properties) -> None:
        """Subscribes to MQTT topics for availability and value topics.
        """
        if reason_code == 0:
            self._logger.debug(
                'Connection accepted -> launch connect handlers')
            _topic_avail = self.codec.get_availability_topic()
            self.client.subscribe(_topic_avail, qos=1)
            for _topic_property in self.codec.get_subscription_topics():
                self.client.subscribe(_topic_property, qos=1)
        else:
            self._logger.warning('[%s] connection refused - reason : %s',
                                 self,
                                 mqtt.connack_string(reason_code))

    def _on_disconnect_callback(self,
                                client: mqtt.Client,
                                userdata: Any,
                                disconnect_flags: mqtt.DisconnectFlags,
                                reason_code: mqtt.ReasonCode,
                                properties: mqtt.Properties) -> None:
        """Subscribes to MQTT topics for availability and value topics.
        """
        if reason_code == 0:
            self._logger.debug('Disconnection occures - rc : %s -> stop loop',
                               reason_code)
            client.loop_stop()
        else:
            self._logger.warning('[%s] disconnection not required with rc "%s"',
                                 self,
                                 reason_code)

    def _handle_values(self, topic: str, payload: bytes) -> None:
        """Handle an incoming sensor value message.

        Decode the message and execute property processors.

        Args:
            topic (str): The topic on which the message was received.
            payload (str): The message payload.

        Raises:
            DecodingException: If an error occurs decoding the message.
        """
        for _handler in self.codec.get_message_handlers(topic):
            if not _handler:
                raise (ValueError(f'No topic set to decode : "{topic}"'))
            _decoder, _virtual_device = _handler
            if _virtual_device is None:
                raise (ValueError(
                    f'No virtual device set for topic : "{topic}"'))
            # Decode value
            _decoded_value = _decoder(self.codec,
                                      topic,
                                      self.codec.fit_payload(payload))
            # Process handle_new_value with the decoded value
            _virtual_device.handle_new_value(_decoded_value, self)

    def _handle_availability(self, payload: str) -> bool:
        """Handle availability message, executing availability processors when status changes.

        Args:
            payload (str): Availability value received in the payload

        Raises:
            DecodingException: If an error occurs decoding the payload
        """
        self._logger.debug('Handle availability message with payload: %s',
                           payload)
        new_avail = self.codec.decode_avail_pl(payload)
        if self.availability != new_avail:
            self.availability = new_avail
            self._logger.debug('Availability updated: %s',  self.availability)
            # Notify
            for _processor in self._avail_proc_list:
                _processor.process_availability_update(self.availability)
        else:
            self._logger.debug('Availability unchanged: %s',
                               self.availability)
        return new_avail

    def publish_message(self, topic: str, message: str) -> None:
        rc: mqtt.MQTTMessageInfo = self.client.publish(topic,
                                                       message,
                                                       qos=1,
                                                       retain=False)
