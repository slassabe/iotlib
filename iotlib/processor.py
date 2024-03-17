#!/usr/local/bin/python3
# coding=utf-8
"""Processor classes for handling device events.

This module defines the VirtualDeviceProcessor abstract base class 
for processing updates from virtual devices and sensors. 

Concrete subclasses should implement the process_value_update() method
to provide custom logic when a device value changes.

Typical usage:

1. Define a custom processor subclass
2. Override process_value_update() 
3. Register it to a virtual device using device.processor_append()
4. The processor will receive value change events via process_value_update()

"""


from iotlib.devconfig import ButtonValues
from iotlib.client import MQTTClient
from iotlib.abstracts import AvailabilityProcessor, VirtualDeviceProcessor
from iotlib.virtualdev import VirtualDevice

PUBLISH_TOPIC_BASE = 'canonical'

class VirtualDeviceLogger(VirtualDeviceProcessor):
    """Logs updates from virtual devices.

    This processor logs a debug message when a virtual 
    device value is updated.

    """

    def process_value_update(self,
                             v_dev: VirtualDevice,
                             bridge) -> None:
        self._logger.debug('[%s] logging device "%s" (property : "%s" - value : "%s")',
                           self,
                           v_dev,
                           v_dev.get_property(),
                           v_dev.value)


class ButtonTrigger(VirtualDeviceProcessor):
    """
    A class that processes button press actions on registered switches.

    This class inherits from the VirtualDeviceProcessor class and provides
    functionality to handle button press events and trigger actions on
    registered virtual switches.

    Attributes:
        _countdown_long (int): The duration of the long press action in seconds.
    """

    def __init__(self, countdown_long=60*10) -> None:
        """
        Initializes a ButtonTrigger instance.

        Parameters:
            countdown_long (int): The duration of the long press action in seconds.
        """
        super().__init__()
        self._countdown_long = countdown_long

    def process_value_update(self, v_dev: VirtualDevice, bridge) -> None:
        """
        Process button press actions on registered switches.

        This method is called on each button value change to trigger 
        actions on the registered virtual switches.

        Parameters:
            v_dev (VirtualDevice): The button device that triggered the action.
            bridge: The bridge object.

        Actions:
            - single press: Start registered switches with default countdown.
            - double press: Start and stop registered switches for countdown_long.
            - long press: Stop registered switches.

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
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(bridge)
        elif v_dev.value == ButtonValues.DOUBLE_ACTION.value:
            self._logger.info('%s -> "start_and_stop" with long period',
                              prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.start_and_stop(self._countdown_long)
        elif v_dev.value == ButtonValues.LONG_ACTION.value:
            self._logger.info('%s -> "trigger_stop"', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_stop(bridge)
        else:
            self._logger.error('%s : action unknown "%s"',
                               prefix,
                               v_dev.value)


class MotionTrigger(VirtualDeviceProcessor):
    '''
    A class that handles motion sensor state changes and triggers registered switches 
    when occupancy is detected.
    '''

    def process_value_update(self,
                             v_dev: VirtualDevice,
                             bridge) -> None:
        """
        Process the value update of a virtual device.

        Args:
            v_dev (VirtualDevice): The virtual device whose value is updated.
            bridge: The bridge object.

        Returns:
            None
        """
        if v_dev.value:
            self._logger.info('[%s] occupancy changed to "%s" '
                              '-> "start_and_stop" on registered switch',
                              v_dev.friendly_name,
                              v_dev.value)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(bridge)
        else:
            self._logger.debug('[%s] occupancy changed to "%s" '
                               '-> nothing to do (timer will stop switch)',
                               v_dev.friendly_name,
                               v_dev.value)


class PropertyPublisher(VirtualDeviceProcessor):
    """
    A class that publishes property updates to an MQTT broker.

    Args:
        client (MQTTClient): The MQTT client used for publishing.
        topic_base (str, optional): The base topic to which the property updates will be published.

    """

    def __init__(self,
                 client: MQTTClient,
                 publish_topic_base: str = None):
        super().__init__()
        self._client = client
        self._publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE

    def process_value_update(self, v_dev, bridge) -> None:
        """
        Publishes the updated value of a virtual device's property to the MQTT broker.

        Args:
            v_dev (VirtualDevice): The virtual device whose property value has been updated.
            bridge: The bridge associated with the virtual device.

        Returns:
            None

        """
        _property_topic = self._publish_topic_base
        _property_topic += '/device/' + v_dev.friendly_name
        _property_topic += '/' + v_dev.get_property().property_node
        _property_topic += '/' + v_dev.get_property().property_name

        self._client.publish(_property_topic,
                             v_dev.value,
                             qos=1, retain=True)


class AvailabilityLogger(AvailabilityProcessor):
    """Logs availability updates of devices.

    This processor logs a message when a device's 
    availability changes.

    """

    def __init__(self, device_name: str):
        super().__init__()
        self.device_name = device_name

    def process_availability_update(self, availability: bool) -> None:
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
                 device_name: str,
                 client: MQTTClient,
                 publish_topic_base: str = None):
        if not isinstance(client, MQTTClient):
            raise TypeError(f"client must be MQTTClient, not {type(client)}")
        if not isinstance(device_name, str):
            raise TypeError(
                f"device_name must be string, not {type(device_name)}")

        super().__init__()
        self._client = client
        _publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE
        self._state_topic = f"{_publish_topic_base}/device/{device_name}/$state"
        self._client.will_set(self._state_topic,
                              'lost',
                              qos=1, retain=True)

    def process_availability_update(self, availability: bool) -> None:
        if availability is None:
            _state_str = 'init'
        elif availability:
            _state_str = 'ready'
        else:
            _state_str = 'disconnected'
        self._client.publish(self._state_topic,
                             _state_str,
                             qos=1, retain=True)
