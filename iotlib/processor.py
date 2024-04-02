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
import threading

from iotlib.devconfig import ButtonValues
from iotlib.abstracts import AvailabilityProcessor, MQTTService, Surrogate, VirtualDeviceProcessor
from iotlib.virtualdev import VirtualDevice, Operable
from iotlib.utils import iotlib_logger

PUBLISH_TOPIC_BASE = 'canonical'


class VirtualDeviceLogger(VirtualDeviceProcessor):
    """Logs updates from virtual devices.

    This processor logs a debug message when a virtual 
    device value is updated.

    """

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        # Implement the abstract method from VirtualDeviceProcessor
        iotlib_logger.debug('[%s] logging device "%s" (property : "%s" - value : "%s")',
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

    def __init__(self,
                 mqtt_service: MQTTService,
                 countdown_long=60*10) -> None:
        """
        Initializes a ButtonTrigger instance.

        Parameters:
            mqtt_service (MQTTService): The MQTT service used for communication.
            countdown_long (int): The duration of the long press action in seconds.
        """
        super().__init__()
        self._mqtt_service = mqtt_service
        self._countdown_long = countdown_long

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        """
        Process button press actions on registered switches.

        This method is called on each button value change to trigger 
        actions on the registered virtual switches.

        Parameters:
            v_dev (VirtualDevice): The button device that triggered the action.

        Actions:
            - single press: Start registered switches with default countdown.
            - double press: Start and stop registered switches for countdown_long.
            - long press: Stop registered switches.

        No return value.
        """
        prefix = f'[{v_dev}] : event "{v_dev.value}" occured'
        if v_dev.value is None:
            iotlib_logger.debug(
                '%s -> discarded', prefix)
            return
        elif v_dev.value == ButtonValues.SINGLE_ACTION.value:
            iotlib_logger.info(
                '%s -> "start_and_stop" with short period', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(mqtt_service=self._mqtt_service)
        elif v_dev.value == ButtonValues.DOUBLE_ACTION.value:
            iotlib_logger.info('%s -> "start_and_stop" with long period',
                               prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(mqtt_service=self._mqtt_service,
                                  on_time=self._countdown_long)
        elif v_dev.value == ButtonValues.LONG_ACTION.value:
            iotlib_logger.info('%s -> "trigger_stop"', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_stop(mqtt_service=self._mqtt_service)
        else:
            iotlib_logger.error('%s : action unknown "%s"',
                                prefix,
                                v_dev.value)


class MotionTrigger(VirtualDeviceProcessor):
    '''
    A class that handles motion sensor state changes and triggers registered switches 
    when occupancy is detected.
    '''

    def __init__(self,
                 mqtt_service: MQTTService) -> None:
        """
        Initializes a MotionTrigger instance.

        Parameters:
            mqtt_service (MQTTService): The MQTT service used for communication.

        Returns:
            None
        """
        super().__init__()
        self._mqtt_service = mqtt_service

    def process_value_update(self,
                             v_dev: VirtualDevice) -> None:
        """
        Process the value update of a virtual device.

        Args:
            v_dev (VirtualDevice): The virtual device whose value is updated.

        Returns:
            None
        """
        if v_dev.value:
            iotlib_logger.info('[%s] occupancy changed to "%s" '
                               '-> "start_and_stop" on registered switch',
                               v_dev.friendly_name,
                               v_dev.value)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(self._mqtt_service,
                                  on_time=_sw.countdown)
        else:
            iotlib_logger.debug('[%s] occupancy changed to "%s" '
                                '-> nothing to do (timer will stop switch)',
                                v_dev.friendly_name,
                                v_dev.value)


class CountdownTrigger(VirtualDeviceProcessor):
    def __init__(self,
                 mqtt_service: MQTTService) -> None:
        """
        Initializes a CountdownTrigger instance.

        Parameters:
            client (MQTTClient): The MQTT client used for communication.

        Returns:
            None
        """
        super().__init__()
        if not isinstance(mqtt_service, MQTTService):
            raise TypeError(
                f"'mqtt_service' must be MQTTService, not {type(mqtt_service)}")
        self._mqtt_service = mqtt_service
        self._stop_timer = None

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        """
        Process the value update of a virtual device.

        Args:
            v_dev (VirtualDevice): The virtual device whose value is updated.

        Returns:
            None
        """
        _countdown = v_dev.countdown
        if _countdown is None:
            iotlib_logger.warning('[%s] cannot process - no countdown set',
                                  self)
            return
        self._remember_to_turn_the_light_off(v_dev,
                                             _countdown)

    def _remember_to_turn_the_light_off(self,
                                        operable: Operable,
                                        when: int) -> None:
        iotlib_logger.debug('[%s] Automatially stop after "%s" sec.',
                            self,  when)
        if not isinstance(when, int) or when <= 0:
            raise TypeError(
                f'Expecting a positive int for period "{when}", not {type(when)}')
        if self._stop_timer:
            self._stop_timer.cancel()    # a timer is allready set, cancel it
        self._stop_timer = threading.Timer(when,
                                           operable.trigger_stop,
                                           [self._mqtt_service])
        self._stop_timer.start()


class PropertyPublisher(VirtualDeviceProcessor):
    """
    A class that publishes property updates to an MQTT broker.

    Args:
        mqtt_service (MQTTService): The MQTT service used for publishing.
        publish_topic_base (str, optional): The base topic to which the property updates will be published.

    """

    def __init__(self,
                 mqtt_service: MQTTService,
                 publish_topic_base: str | None = None):
        super().__init__()
        self._mqtt_service = mqtt_service
        self._publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE

    def process_value_update(self, v_dev) -> None:
        """
        Publishes the updated value of a virtual device's property to the MQTT broker.

        Args:
            v_dev (VirtualDevice): The virtual device whose property value has been updated.

        Returns:
            None

        """
        _property_topic = self._publish_topic_base
        _property_topic += '/device/' + v_dev.friendly_name
        _property_topic += '/' + v_dev.get_property().property_node
        _property_topic += '/' + v_dev.get_property().property_name

        _client = self._mqtt_service.mqtt_client
        _client.publish(_property_topic,
                        v_dev.value,
                        qos=1, retain=True)


class AvailabilityLogger(AvailabilityProcessor):
    """Logs availability updates of devices.

    This processor logs a message when a device's 
    availability changes.

    """

    def __init__(self, debug: bool = False):
        super().__init__()
        self._device_name = None
        self._debug = debug

    def attach(self, bridge: Surrogate) -> None:
        # Implement the abstract method from AvailabilityProcessor
        self._device_name = bridge.codec.device_name

    def process_availability_update(self, availability: bool) -> None:
        # Implement the abstract method from AvailabilityProcessor
        if availability:
            _log_fn = iotlib_logger.info if self._debug else iotlib_logger.debug
            _log_fn("[%s] is available", self._device_name)
        else:
            iotlib_logger.warning(
                "[%s] is unavailable", self._device_name)


class AvailabilityPublisher(AvailabilityProcessor):
    """Processes availability updates from MQTTBridge.

    This processor handles availability updates from a MQTTBridge 
    instance. It publishes the availability status to a MQTT topic.

    """

    def __init__(self,
                 publish_topic_base: str = None):
        if not isinstance(publish_topic_base, str):
            raise TypeError(
                f"publish_topic_base must be string, not {type(publish_topic_base)}")

        super().__init__()
        self._mqtt_service = None
        self._state_topic = None
        self._publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE

    def attach(self, bridge: Surrogate) -> None:
        _device_name = bridge.codec.device_name
        self._mqtt_service = bridge.mqtt_service
        self._state_topic = f"{self._publish_topic_base}/device/{_device_name}/$state"
        _client = self._mqtt_service.mqtt_client
        _client.will_set(self._state_topic,
                         'lost',
                         qos=1, retain=True)

    def process_availability_update(self, availability: bool) -> None:
        if availability is None:
            _state_str = 'init'
        elif availability:
            _state_str = 'ready'
        else:
            _state_str = 'disconnected'
        _client = self._mqtt_service.mqtt_client
        _client.publish(self._state_topic,
                        _state_str,
                        qos=1, retain=True)
