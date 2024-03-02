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

from abc import ABC, ABCMeta, abstractmethod
from iotlib.devconfig import ButtonValues
from iotlib.client import MQTTClient

from . import package_level_logger


class Processor(ABC):
    """Base class for processing events from sensors and devices.
    """
    _logger = package_level_logger

    def __str__(self):
        return f'{self.__class__.__name__} object'


class VirtualDeviceProcessor(Processor, metaclass=ABCMeta):
    """Base class for processing events from virtual devices.

    This class defines the common handle_device_update() method that is called 
    when a sensor value changes or device availability changes.

    Child classes should implement handle_device_update() to handle specific 
    processing logic for the sensor or device type.

    """

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

    - countdown_long: duration (in sec) for "start_and_stop" action on double press

    Virtual switches to control must be passed in 
    registered_list on registration.
    """

    def __init__(self,
                 countdown_long=60*10) -> None:
        super().__init__()
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
            - single press: Start registered switches with default countdown
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
            for _sw in v_dev.sensor_observers:
                _sw.trigger_start()
        elif v_dev.value == ButtonValues.DOUBLE_ACTION.value:
            self._logger.info('%s -> "start_and_stop" with long period',
                              prefix)
            for _sw in v_dev.sensor_observers:
                _sw.start_and_stop(self._countdown_long)
        elif v_dev.value == ButtonValues.LONG_ACTION.value:
            self._logger.info('%s -> "trigger_stop"', prefix)
            for _sw in v_dev.sensor_observers:
                _sw.trigger_stop()
        else:
            self._logger.error('%s : action unknown "%s"',
                               prefix,
                               v_dev.value)


class MotionTrigger(VirtualDeviceProcessor):
    """ Start registered switches when occupency is detected
    """

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
            for _sw in v_dev.sensor_observers:
                _sw.trigger_start()
        else:
            self._logger.debug('[%s] occupancy changed to "%s" '
                               '-> nothing to do (timer will stop switch)',
                               v_dev.friendly_name,
                               v_dev.value)


class PropertyPublisher(VirtualDeviceProcessor):

    def __init__(self,
                 client: MQTTClient,
                 topic_base: str = None):
        super().__init__()
        self._client = client
        self._topic_base = topic_base

    def handle_device_update(self, v_dev) -> None:
        _property_topic = self._topic_base
        _property_topic += '/device/' + v_dev.friendly_name
        _property_topic += '/' + v_dev.get_property().property_node
        _property_topic += '/' + v_dev.get_property().property_name

        self._client.publish(_property_topic,
                             v_dev.value,
                             qos=1, retain=True)


class AvailabilityProcessor(Processor, metaclass=ABCMeta):
    """Abstract base class for processors that handle device availability updates.

    This class provides a common interface for processors that need to react
    to device availability changes reported by a Surrogate instance. 

    Subclasses should implement handle_update() to define custom availability 
    processing behavior.
    """
    @abstractmethod
    def handle_update(self,
                      availability: bool) -> None:
        """Handle an update to the device availability status.

        Args:
            availability (bool): The new availability status of the device.

        Returns:
            None
        """
        raise NotImplementedError


class AvailabilityLogger(AvailabilityProcessor):
    """Logs availability updates of devices.

    This processor logs a message when a device's 
    availability changes.

    """

    def __init__(self, device_name: str):
        super().__init__()
        self.device_name = device_name

    def handle_update(self, availability: bool) -> None:
        if availability:
            self._logger.debug("[%s] is available", self.device_name)
        else:
            self._logger.info("[%s] is unavailable", self.device_name)


class AvailabilityPublisher(AvailabilityProcessor):
    """Processes availability updates from MQTTBridge.

    This processor handles availability updates from a MQTTBridge 
    instance. It publishes the availability status to a MQTT topic.

    """

    def __init__(self,
                 client: MQTTClient,
                 device_name: str,
                 topic_base: str = None):
        super().__init__()
        self._client = client
        self._topic_base = topic_base
        self._state_topic = f"{topic_base}/device/{device_name}/$state"
        self._client.will_set(self._state_topic, 
                              'lost',
                              qos=1, retain=True)

    def handle_update(self,
                      availability: bool) -> None:
        if availability is None:
            _state_str = 'init'
        elif availability:
            _state_str = 'ready'
        else:
            _state_str = 'disconnected'
        self._client.publish(self._state_topic,
                             _state_str,
                             qos=1, retain=True)
