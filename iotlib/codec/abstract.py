#!/usr/local/bin/python3
# coding=utf-8

from abc import abstractmethod, ABC
from collections import defaultdict
from typing import Callable, TypeAlias

from iotlib import package_level_logger
from iotlib.virtualdev import VirtualDevice


MessageHandlerType: TypeAlias = tuple[
    Callable,
    VirtualDevice]
HandlersListType: TypeAlias = dict[str, MessageHandlerType]


class AbstractCodec(ABC):
    _logger = package_level_logger
    def __init__(self,
                 device_name: str,
                 base_topic: str):
        self.device_name = device_name
        self.base_topic = base_topic
        self._message_handler_dict: HandlersListType = defaultdict(list)

    def __str__(self) -> str:
        _dev = self.device_name if hasattr(self, 'device_name') else 'UNSET'
        return f'{self.__class__.__name__} ("{_dev}")'

    def get_subscription_topics(self) -> list[str]:
        """Return the topics the client must subscribe according to message handler set
        """
        return list(self._message_handler_dict.keys())

    def _set_message_handler(self,
                             topic: str,
                             decoder: Callable,
                             vdev: VirtualDevice) -> None:
        """Set a message handler function for a MQTT topic.

        Args:
            topic (str): The MQTT topic to handle.
            decoder (callable): The function to decode messages from the topic.
            vdev (VirtualDevice): The virtual device associated with the topic.

        This method associates a topic with a decoding function, virtual device, 
        and node name. It stores this association in a dictionary self._handler_list
        so that when a message is received on the given topic, the provided decoder
        function can be called to process it and update the virtual device.
        """
        _tuple = (decoder, vdev)
        self._message_handler_dict[topic].append(_tuple)

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

    @abstractmethod
    def decode_avail_pl(self, payload: str) -> bool:
        ''' Decode message received on topic dedicated to availability '''
        raise NotImplementedError

    @abstractmethod
    def get_availability_topic(self) -> str:
        '''Get the topic dedicated to handle availability messages'''
        return NotImplementedError

class DecodingException(Exception):
    """ Exception if message received on wrong topic
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
