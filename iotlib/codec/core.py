#!/usr/local/bin/python3
# coding=utf-8

"""
In the context of device models and protocols, each utilizes a unique 
MQTT-based exchange format for encoding and decoding messages.

- Decoding functionalities play a crucial role in extracting values from 
  messages received from `sensors` and `operables`.
- Encoding functionalities, on the other hand, are employed by `operables` 
  to dispatch commands to the devices.

To handle each protocol effectively and ensure accurate and efficient 
communication, a distinct codec is indispensable.
"""

from collections import defaultdict
from typing import Callable, TypeAlias, Tuple, Dict, Any

from iotlib.abstracts import ICodec, IEncoder
from iotlib.virtualdev import VirtualDevice


MessageHandlerType: TypeAlias = Tuple[
    Callable[..., Any],
    VirtualDevice]
HandlersListType: TypeAlias = Dict[str, MessageHandlerType]


class Codec(ICodec):

    def __init__(self,
                 device_name: str,
                 base_topic: str) -> None:
        """
        Initialize a Codec object.

        Args:
            device_name (str): The name of the device.
            base_topic (str): The base topic for MQTT communication.
        """
        self.device_name = device_name
        self.base_topic = base_topic
        self.encoder: IEncoder = None
        self._managed_virtual_devices: list[VirtualDevice] = []
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

    def get_encoder(self) -> IEncoder | None:
        """Get the encoder for this codec.
        """
        return self.encoder

    def get_managed_virtual_devices(self) -> list[VirtualDevice]:
        """Return the list of virtual devices managed by the codec.
        """
        return self._managed_virtual_devices

    def _add_virtual_device(self, vdev: VirtualDevice) -> None:
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
                             vdev: VirtualDevice) -> None:
        """
        Sets the message handler for a given topic.

        Args:
            topic (str): The topic to set the message handler for.
            decoder (Callable): The decoder function to be used for decoding messages.
            vdev (VirtualDevice): The virtual device associated with the message handler.

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
