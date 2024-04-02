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
from typing import Callable, Optional
import enum
import paho.mqtt.client as mqtt

class MQTTService(ABC):
    """    Abstract class to define the MQTT services used by Surrogate classes
    """
    @property
    @abstractmethod
    def mqtt_client(self) -> mqtt.Client:
        """
        Returns the MQTT client object.
        """
        raise NotImplementedError

    @abstractmethod
    def connect(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        ''' Connect to a MQTT remote broker
        '''
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> mqtt.MQTTErrorCode:
        ''' Disconnect from a MQTT remote broker
        '''
        raise NotImplementedError

    @abstractmethod
    def connect_handler_add(self, handler: Callable) -> None:
        """Adds a connect event handler.

        Args:
            handler: The callback function to handle the connect event.
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect_handler_add(self, handler: Callable) -> None:
        """Adds a disconnect event handler.

        Args:
            handler: The callback function to handle the disconnect event.
        """
        raise NotImplementedError


class AbstractEncoder(ABC):
    """Abstract base class for encoding messages to send on MQTT to IoT devices.
    """

    @abstractmethod
    def get_state_request(self, device_id: Optional[int]) -> tuple[str, str]:
        """Get the current state request for a device.

        Args:
            device_id: The device ID to get the state request for.

        Returns:
            A tuple containing the state request topic and payload or None
            if such a request is not accepted.
        """
        raise NotImplementedError

    @abstractmethod
    def is_pulse_request_allowed(self, device_id: Optional[int]) -> bool:
        """Check if a pulse request is allowed for a device.

        Args:
            device_id: The device ID to check if a pulse request is allowed for.

        Returns:
            True if a pulse request is allowed, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def change_state_request(self, is_on: bool, device_id: Optional[int]) -> tuple[str, str]:
        """
        Constructs a change state request for the device.

        Args:
            is_on (bool): Indicates whether the device should be turned on or off.
            device_id (int | None): The ID of the device. If None, the request is for all devices.
            on_time (int | None): The duration in seconds for which the device should remain on. If None, the device will stay on indefinitely.

        Returns:
            tuple[str, str]: A tuple containing the MQTT topic and the payload in JSON format.
        """
        raise NotImplementedError


class AbstractCodec(ABC):
    '''Abstract base class for decoding messages received on MQTT to IoT devices'''

    @abstractmethod
    def decode_avail_pl(self, payload: str) -> bool:
        '''Decode message received on topic dedicated to availability.

        Args:
            payload (str): The payload of the message received on the availability topic.

        Returns:
            bool: True if the decoding is successful, False otherwise.
        '''
        raise NotImplementedError

    @abstractmethod
    def get_availability_topic(self) -> str:
        '''Return the availability topic the client must subscribe.

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
        mqtt_client (MQTTClient): The MQTT client used for communication.
        codec (AbstractCodec): The codec used for encoding/decoding messages.
    """

    def __init__(self,
                 mqtt_service: MQTTService,
                 codec: AbstractCodec):
        self.mqtt_service = mqtt_service
        self.codec = codec


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
    def process_discovery_update(self, devices: list) -> None:
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
    def process_availability_update(self, availability: bool) -> None:
        """Handle an update to the device availability status.

        Args:
            availability (bool): The new availability status of the device.

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
    def process_value_update(self, v_dev: any) -> None:
        """Handle an update from a virtual device.

        This method is called when a value changes on a virtual 
        device. It should be implemented in child classes to 
        handle specific processing logic for the device type.

        Args:
            v_dev (VirtualDevice): The virtual device instance.

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
    def handle_value(self, value) -> ResultType:
        """
        Handles the received value and performs necessary actions.

        Args:
            value (any): The received value.

        Returns:
            ResultType: The result of handling the value.
        """
        raise NotImplementedError

    @abstractmethod
    def processor_append(self, processor: VirtualDeviceProcessor) -> None:
        """
        Appends a VirtualDeviceProcessor to the list of processors.

        Args:
            processor (VirtualDeviceProcessor): The VirtualDeviceProcessor to append.

        Raises:
            TypeError: If the processor is not an instance of VirtualDeviceProcessor.
        """
        raise NotImplementedError
