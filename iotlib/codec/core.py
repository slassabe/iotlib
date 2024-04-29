#!/usr/local/bin/python3
# coding=utf-8

"""
This module provides the `Codec` class, which is responsible for encoding 
and decoding MQTT messages ccording to the specific formats used by 
different device models and protocols.

Decoding functionalities are crucial for extracting values from messages 
received from sensors and operables.
Encoding functionalities are used by operables to send commands to the devices.

To handle each protocol effectively and ensure accurate and efficient communication,
 a distinct codec is essential.
"""

from collections import defaultdict
from typing import Callable, TypeAlias, Tuple, Dict, Any

from iotlib.abstracts import ICodec,IVirtualDevice


MessageHandlerType: TypeAlias = Tuple[
    Callable[..., Any],
    IVirtualDevice]
HandlersListType: TypeAlias = Dict[str, MessageHandlerType]


class Codec(ICodec):
    """
    The Codec class is responsible for encoding and decoding MQTT messages for a s
    pecific device.

    It manages a list of virtual devices and a dictionary of message handlers, 
    which are functions that handle messages received on specific MQTT topics.
    """

    def __init__(self,
                 device_name: str,
                 base_topic: str) -> None:
        """
        Initializes a new instance of the Codec class.

        This method initializes a new instance of the Codec class with a given device 
        name and a base topic for MQTT communication.

        :param device_name: The name of the device.
        :type device_name: str
        :param base_topic: The base topic for MQTT communication.
        :type base_topic: str
        """
        self.device_name = device_name
        self.base_topic = base_topic
        self._managed_virtual_devices: list[IVirtualDevice] = []
        self._message_handler_dict: HandlersListType = defaultdict(list)

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

    def get_managed_virtual_devices(self) -> list[IVirtualDevice]:
        """Return the list of virtual devices managed by the codec.
        """
        return self._managed_virtual_devices

    def _add_virtual_device(self, vdev: IVirtualDevice) -> None:
        """Add a virtual device to the list of managed virtual devices.
        """
        self._managed_virtual_devices.append(vdev)

    def get_subscription_topics(self) -> list[str]:
        """Return the topics the client must subscribe according to message handler set
        """
        return list(self._message_handler_dict.keys())

    def _set_message_handler(self,
                             topic: str,
                             decoder: Callable,
                             vdev: IVirtualDevice) -> None:
        """
        Sets the message handler for a given topic.

        Args:
            topic (str): The topic to set the message handler for.
            decoder (Callable): The decoder function to be used for decoding messages.
            vdev (IVirtualDevice): The virtual device associated with the message handler.

        This method associates a topic with a decoding function, virtual device, 
        and node name. It stores this association in a dictionary self._handler_list
        so that when a message is received on the given topic, the provided decoder
        function can be called to process it and update the virtual device.
        """
        _tuple = (decoder, vdev)
        self._message_handler_dict[topic].append(_tuple)
        self._add_virtual_device(vdev)

    def get_message_handlers(self, topic: str) -> list[MessageHandlerType]:
        """Get the message handler functions for a given MQTT topic.

        Args:
            topic (str): The MQTT topic to get handlers for.

        Returns:
            list: The list of handler functions for the given topic.
        """
        return self._message_handler_dict[topic]

    @staticmethod
    def fit_payload(payload) -> str:
        """Adjust payload to be decoded, that is, fit in string
        """
        return payload


class DecodingException(Exception):
    """ Exception if message received on wrong topic
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
