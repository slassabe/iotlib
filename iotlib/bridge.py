#!/usr/local/bin/python3
# coding=utf-8

"""
This module contains the MQTTBridge class which extends the Surrogate class.

The MQTTBridge class is responsible for handling MQTT-specific operations. 
It uses an MQTT service instance for MQTT operations and a codec instance for 
encoding and decoding messages.
"""
from typing import Any
import paho.mqtt.client as mqtt

from iotlib.abstracts import IAvailabilityProcessor, IMQTTService, Surrogate
from iotlib.codec.core import DecodingException, ICodec
from iotlib.utils import iotlib_logger


class MQTTBridge(Surrogate):
    """
    MQTTBridge is a class that extends the Surrogate class.

    This class is responsible for handling MQTT-specific operations.

    :ivar mqtt_service: The MQTT service instance.
    :vartype mqtt_service: IMQTTService
    :ivar codec: The codec instance for encoding and decoding messages.
    :vartype codec: ICodec
    """

    def __init__(self,
                 mqtt_service: IMQTTService,
                 codec: ICodec):
        """
        Initialize the MQTTBridge instance.

        :param mqtt_service: The MQTT service instance.
        :type mqtt_service: IMQTTService
        :param codec: The codec instance for encoding and decoding messages.
        :type codec: ICodec
        :raises TypeError: If mqtt_service is not an instance of IMQTTService or codec 
        is not an instance of ICodec.
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be an instance of MQTTService, not {type(mqtt_service)}")
        if not isinstance(codec, ICodec):
            raise TypeError(
                f"codec must be an instance of AbstractCodec, not {type(codec)}")
        super().__init__(mqtt_service, codec)

        self._availability: bool = None
        self._availability_processors: list[IAvailabilityProcessor] = []

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

        :return: True if the bridge is available, False otherwise.
        :rtype: bool
        """
        return self._availability

    @availability.setter
    def availability(self, value: bool) -> None:
        self._availability = value

    def add_availability_processor(self, processor: IAvailabilityProcessor) -> None:
        """
        Appends an Availability Processor instance to the processor list.

        :param processor: The Availability Processor instance to append.
        :type processor: IAvailabilityProcessor
        :raises TypeError: If processor is not an instance of IAvailabilityProcessor.
        :return: None
        """
        if not isinstance(processor, IAvailabilityProcessor):
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
