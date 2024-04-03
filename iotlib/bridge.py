#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines the MQTTBridge class, which serves as a bridge between the MQTTClient and 
AbstractCodec classes.

The MQTTBridge class handles MQTT connections, message callbacks, availability updates, 
and value handling. 
It uses the MQTTClient to connect to an MQTT broker and send/receive messages, and the AbstractCodec 
to encode/decode these messages.

"""

from typing import Any
import paho.mqtt.client as mqtt

from iotlib.utils import iotlib_logger
from iotlib.abstracts import MQTTService, Surrogate, AvailabilityProcessor
from iotlib.codec.core import AbstractCodec, DecodingException


class MQTTBridge(Surrogate):
    """
    Represents an MQTT bridge that connects to an MQTT service and handles incoming messages.

    Args:
        mqtt_service (MQTTService): The MQTT service to connect to.
        codec (AbstractCodec): The codec used for encoding and decoding messages.

    Attributes:
        _availability (bool): The availability status of the bridge.
        _availability_processors (list[AvailabilityProcessor]): List of availability processors.

    """

    def __init__(self,
                 mqtt_service: MQTTService,
                 codec: AbstractCodec):
        if not isinstance(mqtt_service, MQTTService):
            raise TypeError(f"mqtt_service must be an instance of MQTTService, not {type(mqtt_service)}")   
        if not isinstance(codec, AbstractCodec):
            raise TypeError(f"codec must be an instance of AbstractCodec, not {type(codec)}")
        super().__init__(mqtt_service, codec)

        self._availability: bool = None
        self._availability_processors: list[AvailabilityProcessor] = []

        # Set MQTT on_message callbacks
        _client = self.mqtt_service.mqtt_client
        _client.message_callback_add(self.codec.get_availability_topic(),
                                     self._avalability_callback)
        for _topic_property in self.codec.get_subscription_topics():
            _client.message_callback_add(_topic_property,
                                         self._value_callback)
        # Set MQTT connection handlers
        self.mqtt_service.connect_handler_add(self._on_connect_callback)
        self.mqtt_service.disconnect_handler_add(self._on_disconnect_callback)

    def __repr__(self) -> str:
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({_res})'

    def __str__(self) -> str:
        return f'{self.__class__.__name__} obj.'

    @property
    def availability(self) -> bool:
        """
        Get the availability status of the bridge.

        Returns:
            bool: True if the bridge is available, False otherwise.
        """
        return self._availability

    @availability.setter
    def availability(self, value: bool) -> None:
        self._availability = value

    def add_availability_processor(self, processor: AvailabilityProcessor) -> None:
        """Appends an Availability Processor instance to the processor list
        """
        if not isinstance(processor, AvailabilityProcessor):
            _msg = f"Processor must be instance of AvailabilityProcessor, not {type(processor)}"
            raise TypeError(_msg)
        self._availability_processors.append(processor)
        processor.attach(self)

    def _avalability_callback(self,
                              client: mqtt.Client,  # pylint: disable=unused-argument
                              userdata: Any,  # pylint: disable=unused-argument
                              message: mqtt.MQTTMessage) -> None:
        """Callback function for handling availability messages.
        """
        payload = message.payload.decode("utf-8")
        try:
            self._handle_availability(payload)
        except DecodingException as exp:
            iotlib_logger.exception('"[%s]" : Exception occurred decoding : %s / %s',
                                    exp,
                                    message.topic,
                                    payload[:100])

    def _value_callback(self,
                        client: mqtt.Client,   # pylint: disable=unused-argument
                        userdata: Any,   # pylint: disable=unused-argument
                        message: mqtt.MQTTMessage) -> None:
        """Callback function for handling value messages.
        """
        payload = message.payload.decode("utf-8")
        try:
            self._handle_values(message.topic, payload)
        except DecodingException as exp:
            iotlib_logger.exception('"[%s]" : Exception occured decoding : %s / %s',
                                    exp,
                                    message.topic,
                                    payload[:100])

    def _on_connect_callback(self,
                             client: mqtt.Client,   # pylint: disable=unused-argument
                             userdata: Any,   # pylint: disable=unused-argument
                             flags: mqtt.ConnectFlags,   # pylint: disable=unused-argument
                             reason_code: mqtt.ReasonCode,
                             properties: mqtt.Properties,   # pylint: disable=unused-argument
                             ) -> None:
        """Subscribes to MQTT topics for availability and value topics.
        """
        if reason_code == 0:
            iotlib_logger.debug('[%s] Connection accepted -> subscribe',
                                client)
            _topic_avail = self.codec.get_availability_topic()
            _client = self.mqtt_service.mqtt_client
            _client.subscribe(_topic_avail, qos=1)
            for _topic_property in self.codec.get_subscription_topics():
                _client.subscribe(_topic_property, qos=1)
        else:
            iotlib_logger.warning('[%s] connection refused - reason : %s',
                                  self,
                                  mqtt.connack_string(reason_code))

    def _on_disconnect_callback(self,
                                client: mqtt.Client,
                                userdata: Any,   # pylint: disable=unused-argument
                                disconnect_flags: mqtt.DisconnectFlags,   # pylint: disable=unused-argument
                                reason_code: mqtt.ReasonCode,
                                properties: mqtt.Properties,   # pylint: disable=unused-argument
                                ) -> None:
        """Subscribes to MQTT topics for availability and value topics.
        """
        if reason_code == 0:
            iotlib_logger.debug('Disconnection occures - rc : %s -> stop loop',
                                reason_code)
            client.loop_stop()
        else:
            iotlib_logger.warning('[%s] disconnection not required with rc "%s"',
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
                raise ValueError(f'No topic set to decode : "{topic}"')
            _decoder, _virtual_device = _handler
            if _virtual_device is None:
                raise (ValueError(
                    f'No virtual device set for topic : "{topic}"'))
            # Decode value
            _decoded_value = _decoder(self.codec,
                                      topic,
                                      self.codec.fit_payload(payload))
            # Process handle_value with the decoded value
            _virtual_device.handle_value(_decoded_value)

    def _handle_availability(self, payload: str) -> bool:
        """Handle availability message, executing availability processors when status changes.

        Args:
            payload (str): Availability value received in the payload

        Raises:
            DecodingException: If an error occurs decoding the payload
        """
        iotlib_logger.debug('Handle availability message with payload: %s',
                            payload)
        new_avail = self.codec.decode_avail_pl(payload)
        if self.availability != new_avail:
            self.availability = new_avail
            iotlib_logger.debug(
                'Availability updated: %s',  self.availability)
            # Notify
            for _processor in self._availability_processors:
                _processor.process_availability_update(self.availability)
        else:
            iotlib_logger.debug('Availability unchanged: %s',
                                self.availability)
        return new_avail
