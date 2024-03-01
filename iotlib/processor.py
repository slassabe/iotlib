#!/usr/local/bin/python3
# coding=utf-8
"""Processor classes for handling device events.

This module defines the VirtualDeviceProcessor abstract base class 
for processing updates from virtual devices and sensors. 

Concrete subclasses should implement the handle_device_update() method
to provide custom logic when a device value changes.

Typical usage:

1. Define a custom processor subclass
2. Override handle_device_update() 
3. Register it to a virtual device using device.processor_append()
4. The processor will receive value change events via handle_device_update()

"""

from abc import ABC, abstractmethod
from . import package_level_logger


class VirtualDeviceProcessor(ABC):
    """Base class for processing events from sensors and devices.

    This class defines the common handle_device_update() method that is called 
    when a sensor or device value changes.

    Child classes should implement handle_device_update() to handle specific 
    processing logic for the sensor or device type.

    Attributes:
        None

    Methods:
        handle_device_update() - Called on device events. Implemented in child classes.

    Typical implementation will get the new value, execute some logic
    on it, and call methods on registered devices.
    """
    _logger = package_level_logger

    def __str__(self):
        return f'{self.__class__.__name__} object'


    @abstractmethod
    def handle_device_update(self, v_dev) -> None:
        """Handle an update from a virtual device.

        This method is called when a value changes on a virtual 
        device. It should be implemented in child classes to 
        handle specific processing logic for the device type.

        Args:
            v_dev (VirtualDevice): The virtual device instance.

        """
        raise NotImplementedError


class VirtualDeviceLogger(VirtualDeviceProcessor):
    """Logs updates from virtual devices.

    This processor logs a debug message when a virtual 
    device value is updated.

    """

    def handle_device_update(self, v_dev) -> None:
        self._logger.debug('[%s] logging device "%s" (property : "%s" - value : "%s")',
                          self,
                          v_dev,
                          v_dev.get_property(),
                          v_dev.value)
