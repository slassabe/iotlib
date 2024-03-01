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
from iotlib.devconfig import ButtonValues

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


class ButtonTrigger(VirtualDeviceProcessor):
    """ButtonTrigger is used to trigger actions on registered 
    virtual switches based on the type of button press
    on the associated physical button.

    The parameters are:

    - countdown_short: duration (in sec) for "start_and_stop" action on single press  
    - countdown_long: duration (in sec) for "start_and_stop" action on double press

    Virtual switches to control must be passed in 
    registered_list on registration.
    """

    def __init__(self,
                 countdown_short=60*5,
                 countdown_long=60*10) -> None:
        super().__init__()
        self._countdown_short = countdown_short
        self._countdown_long = countdown_long

    def handle_device_update(self, v_dev) -> None:
        """Process button press actions on registered switches.

        This method is called on each button value change to trigger 
        actions on the registered virtual switches:

        Parameters:
            name (str): Name of the button device
            property_str (str): Property name that changed
            value (int): Button press type value 
                (Button.SINGLE_ACTION, Button.DOUBLE_ACTION, Button.LONG_ACTION)
            registered_list (list): List of registered Switch instances

        Actions:
            - single press: Start and stop registered switches for countdown_short
            - double press: Start and stop registered switches for countdown_long
            - long press: Stop registered switches

        No return value.
        """
        prefix = f'[{v_dev}] : event "{v_dev.value}" occured'
        if v_dev.value is None:
            self._logger.debug(
                '%s -> discarded', prefix)
            return
        elif v_dev.value == ButtonValues.SINGLE_ACTION.value:
            self._logger.info(
                '%s -> "start_and_stop" with short period', prefix)
            for _sw in v_dev.switch_observers:
                _sw.start_and_stop(self._countdown_short)
        elif v_dev.value == ButtonValues.DOUBLE_ACTION.value:
            self._logger.info('%s -> "start_and_stop" with long period',
                              prefix)
            for _sw in v_dev.switch_observers:
                _sw.start_and_stop(self._countdown_long)
        elif v_dev.value == ButtonValues.LONG_ACTION.value:
            self._logger.info('%s -> "trigger_stop"', prefix)
            for _sw in v_dev.switch_observers:
                _sw.trigger_stop()
        else:
            self._logger.error('%s : action unknown "%s"',
                               prefix,
                               v_dev.value)


class MotionTrigger(VirtualDeviceProcessor):
    """ Start registered switches when occupency is detected
    """

    def __init__(self, countdown=60*3):
        super().__init__()
        self._countdown = countdown

    def handle_device_update(self, v_dev) -> None:
        '''
        Handle a Motion Sensor state change, turn on the registered switches \
        when occupancy is detected
        '''
        if v_dev.value:
            self._logger.info('[%s] occupancy changed to "%s" '
                              '-> "start_and_stop" on registered switch',
                              v_dev.friendly_name,
                              v_dev.value)
            for _sw in v_dev.switch_observers:
                _sw.start_and_stop(self._countdown)
        else:
            self._logger.debug('[%s] occupancy changed to "%s" '
                               '-> nothing to do (timer will stop switch)',
                               v_dev.friendly_name,
                               v_dev.value)

