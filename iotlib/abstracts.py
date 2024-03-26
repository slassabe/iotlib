#!/usr/local/bin/python3
# coding=utf-8

"""
This module defines an abstract class for codecs used in IoT communication.
It defines the methods that each codec must implement, including decoding messages,
retrieving the topic dedicated to handling availability messages, and retrieving the 
current state of a device.

Note: This module is part of the iotlib library.
"""

from abc import ABC, abstractmethod
import enum

from iotlib.client import MQTTClient


class AbstractEncoder(ABC):
    @abstractmethod
    def get_state_request(self, device_id: int | None) -> tuple[str, str]:
        """Get the current state request for a device.

        Args:
            device_id: The device ID to get the state request for.

        Returns:
            A tuple containing the state request topic and payload or None
            if such a request is not accepted.
        """
        raise NotImplementedError

    @abstractmethod
    def change_state_request(self, is_on: bool, device_id: int | None) -> tuple[str, str]:
        """Get the state change request for a device.

        Args:
            is_on (bool): True to power on, False to power off.
            device_id: The device ID to get the state change request for.

        Returns:
            A tuple containing the state change request topic and payload or None
            if such a request is not accepted.
        """
        raise NotImplementedError

class AbstractCodec(ABC):
    """Abstract base class for codecs used in IoT communication."""

    @abstractmethod
    def get_encoder(self) -> AbstractEncoder| None:
        """Get the encoder for this codec.

        Returns:
            The encoder for this codec.
        """
        raise NotImplementedError

    @abstractmethod
    def decode_avail_pl(self, payload: str) -> bool:
        ''' Decode message received on topic dedicated to availability 

        Args:
            payload (str): The payload of the message received on the availability topic.

        Returns:
            bool: True if the decoding is successful, False otherwise.

        '''
        raise NotImplementedError

    @abstractmethod
    def get_availability_topic(self) -> str:
        '''Get the topic dedicated to handle availability messages

        Returns:
            str: The topic dedicated to handle availability messages.
        '''
        raise NotImplementedError


class Surrogate(ABC):
    """A surrogate class that wraps an MQTT client and codec.

    This class acts as a surrogate for devices that use the given
    MQTT client and codec for communication. It can handle
    encoding/decoding messages to interact with real devices.

    Attributes:
        client (MQTTClient): The MQTT client used for communication.
        codec (AbstractCodec): The codec used for encoding/decoding messages.
    """

    def __init__(self,
                 mqtt_client: MQTTClient,
                 codec: AbstractCodec):
        self.client = mqtt_client
        self.codec = codec

    @abstractmethod
    def publish_message(self, topic: str, payload: str) -> None:
        """Publish a message on the given MQTT topic.

        Args:
            topic (str): The MQTT topic to publish the message on.
            payload (str): The message payload to publish.
        """
        raise NotImplementedError


class DiscoveryProcessor(ABC):
    """
    Abstract base class for discovery processors.

    This class defines the interface for handling updates to the device discovery status.
    Subclasses must implement the `process_discovery_update` method.

    Methods:
        process_discovery_update: Handle an update to the device discovery status.

    """

    def __str__(self):
        return f'{self.__class__.__name__} object'

    @abstractmethod
    def process_discovery_update(self,
                                 devices: list) -> None:
        """Handle an update to the device discovery status.

        Args:
            devices (list): The list of devices discovered.
        """
        raise NotImplementedError


class AvailabilityProcessor(ABC):
    """
    Abstract base class for availability processors.

    This class defines the interface for handling updates to the availability status of a device.
    Subclasses must implement the `process_availability_update` method.

    Methods:
        process_availability_update: Handle an update to the device availability status.

    """

    def __str__(self):
        return f'{self.__class__.__name__} object'

    @abstractmethod
    def attach(self, bridge: Surrogate) -> None:
        """Attach the processor to a bridge instance.

        Args:
            bridge (Surrogate): The bridge instance to attach to.
        """
        raise NotImplementedError

    @abstractmethod
    def process_availability_update(self,
                                    availability: bool) -> None:
        """Handle an update to the device availability status.

        Args:
            availability (bool): The new availability status of the device.
            bridge (Surrogate): The bridge instance receiving availability.

        Returns:
            None
        """
        raise NotImplementedError


class VirtualDeviceProcessor(ABC):
    """
    Abstract base class for virtual device processors.

    This class defines the interface for processing updates from virtual devices.
    Child classes should implement the `process_value_update` method to handle
    specific processing logic for the device type.

    """

    @abstractmethod
    def process_value_update(self,
                             v_dev: any,
                             bridge: Surrogate) -> None:
        """Handle an update from a virtual device.

        This method is called when a value changes on a virtual 
        device. It should be implemented in child classes to 
        handle specific processing logic for the device type.

        Args:
            v_dev (VirtualDevice): The virtual device instance.
            bridge (Surrogate): The bridge instance receiving value.

        """
        raise NotImplementedError


class ResultType(enum.IntEnum):
    """
    Enum representing the result types.

    Attributes:
        IGNORE (int): Represents an ignored result.
        SUCCESS (int): Represents a successful result.
        ECHO (int): Represents a value appearing twice.
    """
    IGNORE = -1
    SUCCESS = 0
    ECHO = 1


class AbstractDevice(ABC):
    """
    An abstract base class for devices in the IoT system.

    This class defines the common interface for all devices in the system.
    Subclasses must implement the `handle_value` and `processor_append` methods.

    """

    @abstractmethod
    def handle_value(self, value, bridge: Surrogate) -> ResultType:
        """
        Handles the given value using the specified bridge.

        Args:
            value: The value to be handled.
            bridge: The bridge to be used for handling the value.

        Returns:
            The result of handling the value.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def processor_append(self, processor: VirtualDeviceProcessor) -> None:
        """
        Appends a VirtualDeviceProcessor to the list of processors.

        Args:
            processor (VirtualDeviceProcessor): The VirtualDeviceProcessor to append.

        Raises:
            NotImplementedError: This method is meant to be overridden by subclasses.
        """
        raise NotImplementedError
