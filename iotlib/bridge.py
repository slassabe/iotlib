#!/usr/local/bin/python3
# coding=utf-8

from abc import abstractmethod, ABCMeta, ABC
from typing import Callable, List, TypeAlias
from collections import defaultdict

from . import package_level_logger
from iotlib.virtualdev import VirtualDevice, ResultType, ProcessingResult
from iotlib.client import MQTTClient


class Surrogate(ABC):
    _logger = package_level_logger

    def __init__(self, mqtt_client: MQTTClient, device_name: str):
        self.client = mqtt_client
        self.device_name = device_name
        self.availability: bool = None
        self.decoded_values: list = None
        # Set MQTT on_message callbacks
        self.client.message_callback_add(self.get_availability_topic(),
                                         self.avalability_callback_cb)
        for _topic_property in self.get_subscription_list():
            self.client.message_callback_add(_topic_property,
                                             self.property_callback_cb)
        # Set MQTT handlers
        self.client.connect_handler_add(self._on_connect_cb)
        self.client.subscribe_handler_add(self.on_subscribe_cb)
        # Disable auto start MQTT session
        #self.client.start()

    def __repr__(self) -> str:
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({_res})'

    def __str__(self) -> str:
        _dev = self.device_name if hasattr(self, 'device_name') else 'UNSET'
        return f'{self.__class__.__name__} ("{_dev}")'

    def is_available(self) -> bool:
        """ check if the device is available
        """
        return self.availability

    def avalability_callback_cb(self, client, userdata, message) -> None:
        payload = message.payload.decode("utf-8")
        self._logger.debug("Availability message received on topic: '%s' - payload: %s",
                           message.topic, payload)
        self._handle_availability(payload)

    def property_callback_cb(self, client, userdata, message) -> None:
        payload = message.payload.decode("utf-8")
        self._logger.debug("Receives property message on topic '%s': %s",
                           message.topic, payload)
        self._handle_values(message.topic, payload)

    def on_subscribe_cb(self, client, userdata, mid, reason_code_list, properties) -> None:
        self._logger.debug('Subscribe request confirmed')

    def _on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        """Subscribes to MQTT topics for availability and value topics.
        """
        self._logger.debug('Connection request accepted -> subscribe')
        _topic_avail = self.get_availability_topic()
        client.subscribe(_topic_avail, qos=1)
        for _topic_property in self.get_subscription_list():
            client.subscribe(_topic_property, qos=1)

    def _handle_values(self, topic, payload) -> list:
        """Handle an incoming sensor value message.

        Decode the message and execute property processors.

        Args:
            topic (str): The topic on which the message was received.
            payload (str): The message payload.

        Raises:
            EncodingException: If an error occurs decoding the message.
        """
        try:
            self.decoded_values = self._decode_values(topic, payload)
            self._logger.debug('Handle value message on topic: %s - payload: %s', 
                               topic, payload)
            # A value is received from the device : force availability to True
            self.availability = True
            return self.decoded_values
        except DecodingException as exp:
            self._logger.exception('"[%s]" : Exception occured decoding : %s / %s',
                                   exp,
                                   topic,
                                   payload[:100])

    def _handle_availability(self, payload: str) -> bool:
        """Handle availability message, executing availability processors when status changes.

        Args:
            payload (str): Availability value received in the payload

        Raises:
            EncodingException: If an error occurs decoding the payload
        """
        try:
            new_avail = self._decode_avail_pl(payload)
            if self.availability != new_avail:
                self.availability = new_avail
                self._logger.debug('Availability updated: %s',  self.availability)
            else:
                self._logger.debug('Availability unchanged: %s',  self.availability)
            return new_avail
        except DecodingException as exp:
            self._logger.exception('"[%s]" : Exception occured decoding : %s',
                                   exp,
                                   payload)

    @abstractmethod
    def get_availability_topic(self) -> str:
        """Return the availability topic the client must subscribe
        """

    @abstractmethod
    def get_subscription_list(self) -> list:
        """Return the value topics the client must subscribe
        """

    @abstractmethod
    def _decode_avail_pl(self, payload: str) -> bool:
        ''' Decode message received on topic dedicated to availability '''
        raise NotImplementedError

    @abstractmethod
    def _decode_values(self, topic: str, payload: str) -> list:
        """Decode an incoming value message.

        Decode the payload and return a list of (node, property, value) 
        tuples for any matches.


        Args:
            topic (str): The message topic.
            payload (str): The message payload.

        Returns:
            list: A list of (node, property, value) tuples.

        """
        raise NotImplementedError


class Connector(Surrogate):
    def __init__(self, mqtt_client: MQTTClient, device_name: str):
        self._message_handler_dict = defaultdict(list)
        super().__init__(mqtt_client, device_name)

    def get_availability_topic(self) -> str:
        return "NOT_IMPLEMENTED"

    def get_subscription_list(self) -> list:
        """Return the topics the client must subscribe
        * <base_topic>/<device_name> : to get device property values
        """
        _list = list(self._message_handler_dict.keys())
        self._logger.debug("Subscription list is : %s", _list)
        return _list

    def _set_message_handler(self,
                     topic: str,
                     decoder: Callable,
                     vdev: VirtualDevice,
                     node: str) -> None:
        """Set a message handler function for a MQTT topic.

        Args:
            topic (str): The MQTT topic to handle.
            decoder (callable): The function to decode messages from the topic.
            vdev (VirtualDevice): The virtual device associated with the topic.
            node (str): The device node that the topic is for.

        This method associates a topic with a decoding function, virtual device, 
        and node name. It stores this association in a dictionary self._handler_list
        so that when a message is received on the given topic, the provided decoder
        function can be called to process it and update the virtual device.
        """
        _tuple = (decoder, vdev, node)
        self._message_handler_dict[topic].append(_tuple)

    def _get_message_handler(self, topic: str) -> list:
        """Get the message handler functions for a given MQTT topic.

        Args:
            topic (str): The MQTT topic to get handlers for.

        Returns:
            list: The list of handler functions for the given topic.
        """
        return self._message_handler_dict[topic]


    def _decode_values(self, topic: str, payload: str) -> ProcessingResult:
        """Decode values from a Tasmota MQTT message payload.

        Given a topic and payload, look up the associated decoder function
        and virtual device. Call the decoder to extract values from the 
        payload. Pass the decoded values to the virtual device to update
        its state.

        Args:
            topic (str): The message topic
            payload (str): The message payload

        Returns:
            list: List of (node, property, value) tuples if decoding was
            successful, else empty list.
        """
        _decoded_values = list()
        for _handler in self._get_message_handler(topic):
            if not _handler:
                raise(ValueError(f'No topic set to decode : "{topic}"'))
            _decoder, _virtual_device, _node = _handler
            if _virtual_device is None:
                raise(ValueError(f'No virtual device set for topic : "{topic}"'))
            # Decode value
            _decoded_value = _decoder(self, topic, self.fit_payload(payload))
            # Process handle_new_value with the decoded value
            _process_result = _virtual_device.handle_new_value(_decoded_value)

            if _process_result.type is ResultType.SUCCESS:
                _decoded_values.append((_node, 
                                        _process_result.property, 
                                        _process_result.value))
            else:
                return list()
        return _decoded_values

    def fit_payload(self, payload) -> str:
        """Adjust payload to be decoded, that is fit in string
        """
        return payload

class DecodingException(Exception):
    """ Exception if message received on wrong topic
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
