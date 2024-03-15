#!/usr/local/bin/python3
# coding=utf-8

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, TypeAlias

from iotlib import package_level_logger
from iotlib.client import MQTTClient


class AbstractCodec(ABC):
    @abstractmethod
    def decode_avail_pl(self, payload: str) -> bool:
        ''' Decode message received on topic dedicated to availability '''
        raise NotImplementedError

    @abstractmethod
    def get_availability_topic(self) -> str:
        '''Get the topic dedicated to handle availability messages'''
        return NotImplementedError

    @abstractmethod
    def get_state_request(self, device_id: int | None) -> tuple[str, str]:
        """Get the current state request for a device.
    
        Args:
            device_id: The device ID to get the state request for.
        
        Returns:
            A tuple containing the state request topic and payload or None
            if such a request is not accepted.
        """
        return NotImplementedError

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
        return NotImplementedError


class Surrogate(ABC):
    def __init__(self,
                 mqtt_client: MQTTClient,
                 codec: AbstractCodec):
        self.client = mqtt_client
        self.codec = codec

    @abstractmethod
    def publish_message(self, topic: str, message: str) -> None:
        return NotImplementedError



class AvailabilityProcessor(ABC):
    """Abstract base class for processors that handle device availability updates.

    This class provides a common interface for processors that need to react
    to device availability changes reported by a Surrogate instance. 

    Subclasses should implement handle_update() to define custom availability 
    processing behavior.
    """
    _logger = package_level_logger

    def __str__(self):
        return f'{self.__class__.__name__} object'

    @abstractmethod
    def process_availability_update(self,
                      availability: bool) -> None:
        """Handle an update to the device availability status.

        Args:
            availability (bool): The new availability status of the device.

        Returns:
            None
        """
        raise NotImplementedError


class VirtualDeviceProcessor(ABC):
    """Base class for processing events from virtual devices.

    This class defines the common process_value_update() method that is called 
    when a sensor value changes or device availability changes.

    Child classes should implement process_value_update() to handle specific 
    processing logic for the sensor or device type.

    """
    _logger = package_level_logger

    def __str__(self):
        return f'{self.__class__.__name__} object'

    @abstractmethod
    def process_value_update(self, v_dev, bridge) -> None:
        """Handle an update from a virtual device.

        This method is called when a value changes on a virtual 
        device. It should be implemented in child classes to 
        handle specific processing logic for the device type.

        Args:
            v_dev (VirtualDevice): The virtual device instance.

        """
        raise NotImplementedError
