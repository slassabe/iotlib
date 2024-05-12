#!/usr/local/bin/python3
# coding=utf-8

"""
Module containing processor classes for handling virtual devices.

This module provides classes for processing virtual devices. These classes 
implement the IVirtualDeviceProcessor interface and provide specific functionality 
for handling virtual devices.

The primary class in this module is the VirtualDeviceLogger. This class logs 
the actions performed on virtual devices and can be used for debugging and tracking purposes.

:Example: 

.. code-block:: python

    v_switch = Switch()
    factory = CodecFactory()
    codec = factory.create_instance(model=Model.ZB_MINI,
                                    protocol=Protocol.Z2M,
                                    device_name='SWITCH_PLUG',
                                    v_switch=v_switch)
    bridge = iotlib.bridge.MQTTBridge(client, codec)
    # Create a logger instance for the virtual switch
    logger = VirtualDeviceLogger()
    v_switch.processor_append(logger)

The example above shows how to use the VirtualDeviceLogger .
"""

from iotlib.abstracts import (IAvailabilityProcessor, IMQTTBridge,
                              IMQTTService, IVirtualDeviceProcessor)
from iotlib.devconfig import ButtonValues
from iotlib.utils import iotlib_logger
from iotlib.virtualdev import Button, Motion, VirtualDevice

PUBLISH_TOPIC_BASE = "canonical"

class VirtualDeviceProcessor(IVirtualDeviceProcessor):
    def compatible_with_device(
        self, v_dev: any
    ) -> bool:  # pylint: disable=unused-argument
        """
        Checks if the given virtual device is compatible with this processor.

        :param v_dev: The virtual device to check compatibility with.
        :type v_dev: any
        :return: True if the virtual device is compatible, False otherwise.
        :rtype: bool
        """
        return False

class VirtualDeviceLogger(VirtualDeviceProcessor):
    """
    Logs updates from virtual devices.

    This processor logs a debug message when a virtual device value is updated.

    :ivar logger: The logger instance used to log debug messages.
    :vartype logger: logging.Logger
    """

    def __init__(self, debug: bool = False):
        """
        Initializes a new instance of the VirtualDeviceLogger class.

        This method initializes a new instance of the VirtualDeviceLogger class. If the debug
        parameter is set to True, the logger will log debug messages.

        :param debug: A flag indicating whether to log debug messages, defaults to False.
        :type debug: bool, optional
        """
        super().__init__()
        self._debug = debug

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        # Implement the abstract method from VirtualDeviceProcessor
        _log_fn = iotlib_logger.info if self._debug else iotlib_logger.debug
        _log_fn(
            '-> Logging virtual device (friendly_name : "%s" - property : "%s" - value : "%s")',
            v_dev.friendly_name,
            v_dev.get_property(),
            v_dev.value,
        )

    def compatible_with_device(self, v_dev: VirtualDevice) -> None:
        # Define device compatibility for this processor
        return True


class ButtonTrigger(VirtualDeviceProcessor):
    """This processor triggers button actions on virtual devices when their state changes."""

    def __init__(self, mqtt_service: IMQTTService, countdown_long=60 * 10) -> None:
        """
        Initializes a new instance of the ButtonTrigger class.

        This method initializes a new instance of the ButtonTrigger class with a given button map.
        The button map is a dictionary mapping button states to actions.

        :param button_map: A dictionary mapping button states to actions.
        :type button_map: Dict[str, Callable]
        """
        super().__init__()
        self._mqtt_service = mqtt_service
        self._countdown_long = countdown_long

    def compatible_with_device(self, v_dev: VirtualDevice) -> None:
        # Define device compatibility for this processor
        if not isinstance(v_dev, Button):
            return False
        return True

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        """
        Processes a value update from a virtual device.

        This method takes a virtual device as input and triggers the appropriate action
        based on the device's state.

        :param v_dev: The virtual device whose value has been updated.
        :type v_dev: VirtualDevice

        Actions:
            - single press: Start registered switches with default countdown.
            - double press: Start and stop registered switches for countdown_long.
            - long press: Stop registered switches.
        """
        prefix = f'[{v_dev}] : event "{v_dev.value}" occured'
        if v_dev.value is None:
            iotlib_logger.debug("%s -> discarded", prefix)
            return
        if v_dev.value == ButtonValues.SINGLE_ACTION.value:
            iotlib_logger.info('%s -> "start_and_stop" with short period', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(mqtt_service=self._mqtt_service)
        elif v_dev.value == ButtonValues.DOUBLE_ACTION.value:
            iotlib_logger.info('%s -> "start_and_stop" with long period', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(
                    mqtt_service=self._mqtt_service, on_time=self._countdown_long
                )
        elif v_dev.value == ButtonValues.LONG_ACTION.value:
            iotlib_logger.info('%s -> "trigger_stop"', prefix)
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_stop(mqtt_service=self._mqtt_service)
        else:
            iotlib_logger.error('%s : action unknown "%s"', prefix, v_dev.value)


class MotionTrigger(VirtualDeviceProcessor):
    """
    A class that handles motion sensor state changes and triggers registered switches
    when occupancy is detected.
    """

    def __init__(self, mqtt_service: IMQTTService) -> None:
        """
        Initializes a MotionTrigger instance.

        :param mqtt_service: The MQTT service to be used for communication.
        :type mqtt_service: IMQTTService
        """
        super().__init__()
        self._mqtt_service = mqtt_service

    def compatible_with_device(self, v_dev: VirtualDevice) -> None:
        # Define device compatibility for this processor
        if not isinstance(v_dev, Motion):
            return False
        return True

    def process_value_update(self, v_dev: VirtualDevice) -> None:
        """
        Process the value update of a virtual device.

        :param v_dev: The virtual device whose value has been updated.
        :type v_dev: VirtualDevice
        """
        if v_dev.value:
            iotlib_logger.info(
                '[%s] occupancy changed to "%s" '
                '-> "start_and_stop" on registered switch',
                v_dev.friendly_name,
                v_dev.value,
            )
            for _sw in v_dev.get_sensor_observers():
                _sw.trigger_start(self._mqtt_service, on_time=_sw.countdown)
        else:
            iotlib_logger.debug(
                '[%s] occupancy changed to "%s" '
                "-> nothing to do (timer will stop switch)",
                v_dev.friendly_name,
                v_dev.value,
            )


class PropertyPublisher(VirtualDeviceProcessor):
    """A class that publishes property updates to an MQTT broker."""

    def __init__(
        self, mqtt_service: IMQTTService, publish_topic_base: str | None = None
    ):
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given MQTT service
        and an optional publish topic base.

        :param mqtt_service: The MQTT service to be used for communication.
        :type mqtt_service: IMQTTService
        :param publish_topic_base: The base topic for publishing messages. Default base topic is
            used if set to None.
        :type publish_topic_base: str | None, optional
        """

        super().__init__()
        self._mqtt_service = mqtt_service
        self._publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE

    def process_value_update(self, v_dev) -> None:
        """
        Publishes the updated value of a virtual device's property to the MQTT broker.

        :param v_dev: The virtual device whose value has been updated.
        :type v_dev: VirtualDevice
        """
        _property_topic = self._publish_topic_base
        _property_topic += "/device/" + v_dev.friendly_name
        _property_topic += "/" + v_dev.get_property().property_node
        _property_topic += "/" + v_dev.get_property().property_name

        _client = self._mqtt_service.mqtt_client
        _client.publish(_property_topic, v_dev.value, qos=1, retain=True)

    def compatible_with_device(self, v_dev: VirtualDevice) -> None:
        # Define device compatibility for this processor
        return True


class AvailabilityLogger(IAvailabilityProcessor):
    """Logs availability updates of devices.

    This processor logs a message when a device's
    availability changes.

    """

    def __init__(self, debug: bool = False):
        super().__init__()
        self._debug = debug

    def attach(self, bridge: IMQTTBridge) -> None:
        # Implement the abstract method from IAvailabilityProcessor
        pass

    def process_availability_update(self, availability: bool, device_name: str) -> None:
        # Implement the abstract method from IAvailabilityProcessor
        if availability:
            _log_fn = iotlib_logger.info if self._debug else iotlib_logger.debug
            _log_fn("[%s] is available", device_name)
        else:
            iotlib_logger.warning("[%s] is unavailable", device_name)


class AvailabilityPublisher(IAvailabilityProcessor):
    """Processes availability updates from MQTTBridge.

    This processor handles availability updates from a MQTTBridge
    instance. It publishes the availability status to a MQTT topic.

    """

    def __init__(self, publish_topic_base: str | None = None):
        if not isinstance(publish_topic_base, str):
            raise TypeError(
                f"publish_topic_base must be string, not {type(publish_topic_base)}"
            )

        super().__init__()
        self._mqtt_service = None
        self._state_topic = None
        self._publish_topic_base = publish_topic_base or PUBLISH_TOPIC_BASE

    def attach(self, bridge: IMQTTBridge) -> None:
        # Implement the abstract method from IAvailabilityProcessor
        _device_name = bridge.codec.device_name
        self._mqtt_service = bridge.mqtt_service
        self._state_topic = f"{self._publish_topic_base}/device/{_device_name}/$state"
        _client = self._mqtt_service.mqtt_client
        _client.will_set(self._state_topic, "lost", qos=1, retain=True)

    def process_availability_update(self, availability: bool, device_name: str) -> None:
        # Implement the abstract method from IAvailabilityProcessor
        if availability is None:
            _state_str = "init"
        elif availability:
            _state_str = "ready"
        else:
            _state_str = "disconnected"
        _client = self._mqtt_service.mqtt_client
        _client.publish(self._state_topic, _state_str, qos=1, retain=True)
