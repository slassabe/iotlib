#!/usr/local/bin/python3
# coding=utf-8

"""
This module contains abstract base classes for various components of an IoT system.

These classes define the common interfaces for MQTT services, message encoders and decoders,
device surrogates, discovery and availability processors, virtual device processors, and devices.

Each class has its own specific methods that need to be implemented in any concrete subclasses.

"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
import enum
import paho.mqtt.client as mqtt

class IMQTTService(ABC):
    """    Interface for the MQTT services used by Surrogate classes
    """
    @property
    @abstractmethod
    def mqtt_client(self) -> mqtt.Client:
        """
        Returns the MQTT client object.

        :return: The MQTT client object.
        :rtype: mqtt.Client
        """

    @abstractmethod
    def connect(self, properties: Optional[mqtt.Properties] = None) -> mqtt.MQTTErrorCode:
        """
        Connect to a MQTT remote broker.

        :param properties: The properties for the MQTT connection, defaults to None
        :type properties: Optional[mqtt.Properties]
        :return: The MQTT error code for the connection attempt.
        :rtype: mqtt.MQTTErrorCode
        """

    @abstractmethod
    def disconnect(self) -> mqtt.MQTTErrorCode:
        """
        Disconnect from a MQTT remote broker.

        :return: The MQTT error code for the disconnection attempt.
        :rtype: mqtt.MQTTErrorCode
        """

    @abstractmethod
    def connect_handler_add(self, handler: Callable) -> None:
        """
        Adds a connect event handler.

        :param handler: The callback function to handle the connect event.
        :type handler: Callable
        :return: None
        """

    @abstractmethod
    def disconnect_handler_add(self, handler: Callable) -> None:
        """
        Adds a disconnect event handler.

        :param handler: The callback function to handle the disconnect event.
        :type handler: Callable
        :return: None
        """


class IEncoder(ABC):
    """Interface for encoding messages to send on MQTT to IoT devices.
    """

    @abstractmethod
    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        """
        Get the current state request for a device.

        :param device_id: The device ID to get the state request for.
        :type device_id: Optional[int]
        :return: A tuple containing the state request topic and payload or None if such a request 
            is not accepted.
        :rtype: tuple[str, str]
        """

    @abstractmethod
    def is_pulse_request_allowed(self, device_id: Optional[int]) -> bool:
        """
        Check if a pulse request is allowed for a device.

        :param device_id: The device ID to check if a pulse request is allowed for.
        :type device_id: Optional[int]
        :return: True if a pulse request is allowed, False otherwise.
        :rtype: bool
        """

    @abstractmethod
    def change_state_request(self, is_on: bool, device_id: Optional[int]) -> tuple[str, str]:
        """
        Constructs a change state request for the device.

        :param is_on: Indicates whether the device should be turned on or off.
        :type is_on: bool
        :param device_id: The ID of the device. If None, the request is for all devices.
        :type device_id: Optional[int]
        :return: A tuple containing the MQTT topic and the payload in JSON format.
        :rtype: tuple[str, str]
        """

    @abstractmethod
    def device_configure_message(self) -> Optional[tuple[str, str]]:
        """Configure the device before using it
    
        :return: A tuple containing the backlog command and topic
        :rtype: tuple[str, str]
        """


class ICodec(ABC):
    '''Interface for decoding messages received on MQTT to IoT devices'''

    @abstractmethod
    def decode_avail_pl(self, payload: str) -> bool:
        """
        Decode message received on topic dedicated to availability.

        :param payload: The payload of the message received on the availability topic.
        :type payload: str
        :return: True if the decoding is successful, False otherwise.
        :rtype: bool
        """

    @abstractmethod
    def get_availability_topic(self) -> str:
        """
        Return the availability topic the client must subscribe.

        :return: The topic dedicated to handle availability messages.
        :rtype: str
        """


class IMQTTBridge:
    """A surrogate class that wraps an MQTT client and codec.

    This class acts as a surrogate for devices that use the given
    MQTT client and codec for communication. It can handle
    encoding/decoding messages to interact with real devices.
    """

    @property
    @abstractmethod
    def availability(self) -> bool:
        """
        Get the availability status of the bridge.

        :return: True if the bridge is available, False otherwise.
        :rtype: bool
        """
        pass

class IDiscoveryProcessor(ABC):
    """
    Interface for discovery processors.

    This interface defines the methods that a discovery processor should implement.
    """

    @abstractmethod
    def process_discovery_update(self, devices: list) -> None:
        """
        Process a discovery update.

        This method is called when a discovery update is received. It should handle the
        list of devices and perform any necessary processing.

        :param devices: The list of devices discovered.
        :type devices: list
        """


class IAvailabilityProcessor(ABC):
    """Interface for availability processors.

    Subclasses must implement the `process_availability_update` method.
    """

    @abstractmethod
    def attach(self, bridge: IMQTTBridge) -> None:
        """
        Attach the processor to a bridge instance.

        :param bridge: The bridge instance to attach to.
        :type bridge: Surrogate
        :return: None
        """

    @abstractmethod
    def process_availability_update(self, availability: bool) -> None:
        """
        Handle an update to the device availability status.

        :param availability: The new availability status of the device.
        :type availability: bool
        :return: None
        """


class IVirtualDeviceProcessor(ABC):
    """Interface for virtual device processors.

    This class defines the interface for processing updates from virtual devices.
    Child classes should implement the `process_value_update` method to handle
    specific processing logic for the device type.

    """

    @abstractmethod
    def process_value_update(self, v_dev: any) -> None:
        """
        Handle an update from a virtual device.

        This method is called when a value changes on a virtual 
        device. It should be implemented in child classes to 
        handle specific processing logic for the device type.

        :param v_dev: The virtual device instance.
        :type v_dev: any
        :return: None
        """

    def compatible_with_device(self, v_dev: any) -> bool: # pylint: disable=unused-argument
        """
        Checks if the given virtual device is compatible with this processor.

        :param v_dev: The virtual device to check compatibility with.
        :type v_dev: any
        :return: True if the virtual device is compatible, False otherwise.
        :rtype: bool
        """
        return False

class ResultType(enum.IntEnum):
    """
    Enum representing the result types.

    :cvar IGNORE: Represents an ignored result.
    :cvar SUCCESS: Represents a successful result.
    :cvar ECHO: Represents a value appearing twice.
    """
    IGNORE = -1
    SUCCESS = 0
    ECHO = 1


class IVirtualDevice(ABC):
    """Interface for virtual devices in the IoT system.

    This class defines the common interface for all devices in the system.
    Subclasses must implement the `handle_value` and `processor_append` methods.

    """

    @abstractmethod
    def handle_value(self, value) -> ResultType:
        """
        Handles the received value and performs necessary actions.

        :param value: The received value.
        :type value: Any
        :return: The result of handling the value.
        :rtype: ResultType
        """

    @abstractmethod
    def processor_append(self, processor: IVirtualDeviceProcessor) -> None:
        """
        Appends a VirtualDeviceProcessor to the list of processors.

        :param processor: The VirtualDeviceProcessor to append.
        :type processor: VirtualDeviceProcessor
        :raises TypeError: If the processor is not an instance of VirtualDeviceProcessor.
        :return: None
        """
