#!/usr/local/bin/python3
# coding=utf-8
"""

Virtual devices serve as an abstraction layer over physical devices, facilitating interoperability
across different types of devices. These virtual devices are organized into a hierarchical 
structure as follows:

Sensors: These virtual devices are responsible for measuring and reporting various 
environmental conditions. They include:

- Temperature Sensor
- Humidity Sensor
- Light Sensor
- Conductivity Sensor
- Button Sensor
- Motion Sensor
- Analog-to-Digital Converter

Operables: These virtual devices are capable of performing certain actions. They include:

- Alarm
- Switch

Each physical device is associated with one or more virtual devices, which handle the processing 
and management of data. 
For instance, an air sensor might be associated with a Temperature Sensor and a Humidity Sensor 
virtual device, which handle temperature and humidity data respectively. This support is provided 
by the VirtualDevice class.

"""

import enum
import threading
import time
from abc import ABCMeta, abstractmethod
from typing import Optional

from iotlib.abstracts import (IEncoder, IMQTTService, IVirtualDevice,
                              IVirtualDeviceProcessor, ResultType)
from iotlib.devconfig import ButtonValues, PropertyConfig
from iotlib.utils import iotlib_logger


class VirtualDevice(IVirtualDevice, metaclass=ABCMeta):
    """Virtual devices serve as an abstraction layer over physical devices,
    facilitating interoperability across different types of devices.
    """

    QUIET_MODE_DELAY = 60 * 1  # Delay in seconds before the virtual device is updated

    def __init__(self, friendly_name: str, quiet_mode: bool) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given friendly name
        and a quiet mode flag.

        :param friendly_name: The friendly name to be used for the virtual device.
        :type friendly_name: str
        :param quiet_mode: A flag indicating whether the virtual device should operate in
            quiet mode.
        :type quiet_mode: bool
        """
        if friendly_name is not None:
            assert isinstance(
                friendly_name, str
            ), f"Bad value for friendly_name : {friendly_name} of type {type(friendly_name)}"
        self.friendly_name = friendly_name
        self._value = None
        self._quiet_mode = quiet_mode
        self._last_updated = 0 if not self._quiet_mode else time.time()
        self._encoder = None
        # List of processors associated with this device
        self._processor_list: list[IVirtualDeviceProcessor] = []

    def __repr__(self):
        _attr_keys = ("friendly_name", "value", "quiet_mode")
        attrs = [f"{attr}={getattr(self, attr)}" for attr in _attr_keys]
        return f"{self.__class__.__name__}({', '.join(attrs)})"

    def __str__(self):
        return f"{self.__class__.__name__} ({self.friendly_name} | value: {self.value})"

    @property
    def value(self):
        """
        Gets the current value of the virtual device.

        This method returns the current value of the virtual device.

        :return: The current value of the virtual device.
        :rtype: Any
        """
        return self._value

    def _validate_value_type(self, value: any):
        _property = self.get_property()
        _type_cast = self.get_property().property_type
        if not isinstance(value, _type_cast):
            raise TypeError(
                f"Value {value} is not of type {_type_cast} for property {_property}"
            )

    @value.setter
    def value(self, value):
        """
        Sets the value of the device.

        This method sets the value of the device. It validates the type of the value
        before setting it.

        :param value: The value to set.
        :type value: Any
        :raises TypeError: If the value is not of the expected type.
        """
        self._validate_value_type(value)
        self._value = value

    @property
    def encoder(self) -> Optional[IEncoder]:
        """
        Gets the encoder for the device.

        This property returns the encoder that has been set for the device. The encoder is used to
        encode values before sending them to the device.

        :return: The encoder for the device, or `None` if no encoder has been set.
        :rtype: Optional[IEncoder]
        """
        return self._encoder

    @encoder.setter
    def encoder(self, encoder: IEncoder) -> None:
        """
        Sets the encoder for the device.

        This method sets the encoder for the device. It validates the type of the encoder
        before setting it.

        :param encoder: The encoder to set.
        :type encoder: IEncoder
        :raises TypeError: If the encoder is not of the expected type.
        """
        if not isinstance(encoder, IEncoder):
            raise TypeError(
                f"Encoder must be instance of AbstractEncoder, not {type(encoder)}"
            )
        self._encoder = encoder

    @property
    def quiet_mode(self) -> bool:
        """
        Gets the quiet mode flag.
        """
        return self._quiet_mode

    @quiet_mode.setter
    def quiet_mode(self, quiet_mode: bool) -> None:
        """
        Sets the quiet mode flag.
        """
        if not isinstance(quiet_mode, bool):
            raise TypeError(f"quiet_mode must be boolean, not {type(quiet_mode)}")
        self._quiet_mode = quiet_mode
        self._last_updated = 0 if self._quiet_mode else time.time()

    def handle_value(self, value) -> ResultType:
        # Implement the abstract method from AbstractDevice class
        def throttling_disabled():
            if not self._quiet_mode:
                return True
            _now = time.time()
            _time_delta = _now - self._last_updated
            self._last_updated = _now
            iotlib_logger.warning(
                "Delta time : %s -> disabled : %s",
                _time_delta,
                _time_delta < self.QUIET_MODE_DELAY,
            )
            return _time_delta < self.QUIET_MODE_DELAY

        if value is None:
            # No relevant value received (can be info on device like battery level), ignore
            return ResultType.IGNORE
        if (self.value == value) and throttling_disabled():
            iotlib_logger.debug("Throttling_disabled")
            return ResultType.ECHO
        # else:
        self.value = value
        for _processor in self._processor_list:
            iotlib_logger.debug("Execute processor : %s", _processor)
            _processor.process_value_update(self)
        return ResultType.SUCCESS

    def processor_append(self, processor: IVirtualDeviceProcessor) -> None:
        # Implement the abstract method from AbstractDevice class
        if not isinstance(processor, IVirtualDeviceProcessor):
            raise TypeError(
                f"Processor must be instance of Processor, not {type(processor)}"
            )
        if not processor.compatible_with_device(self):
            raise TypeError(
                f"Processor {processor} is not compatible with {self.__class__.__name__}"
            )

        self._processor_list.append(processor)

    @abstractmethod
    def get_property(self) -> str:
        """
        Gets the property of the device.

        This method returns the property of the device.

        :return: The property of the device.
        :rtype: str
        """


class Operable(VirtualDevice):
    """Root implementation of a virtual Operable device (Switch or Alarm)"""

    def __init__(
        self,
        friendly_name: str = None,
        quiet_mode: bool = False,
        countdown: Optional[int] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given friendly name, a quiet
        mode flag, and an optional countdown.

        :param friendly_name: The friendly name to be used for the virtual device, defaults to None.
        :type friendly_name: str, optional
        :param quiet_mode: A flag indicating whether the virtual device should operate in quiet
            mode, defaults to False.
        :type quiet_mode: bool, optional
        :param countdown: The countdown value for the virtual device, defaults to None.
        :type countdown: Optional[int], optional
        """
        if countdown is not None:
            if not isinstance(countdown, int):
                raise TypeError(f"countdown must be integer, not {type(countdown)}")
            if not countdown > 0:
                raise ValueError(f"countdown must be positive integer, not {countdown}")
        super().__init__(friendly_name, quiet_mode=quiet_mode)
        self._device_id = None
        self._stop_timer = None
        self._countdown = countdown
        self._stop_timer = None

    @property
    def device_id(self) -> Optional[int]:
        """Gets the device ID.

        :return: The device ID of the virtual device.
        :rtype: int | None
        """
        return self._device_id

    @device_id.setter
    def device_id(self, value: int) -> None:
        """Sets the device ID.

        :param value: The device ID to set.
        :type value: int
        """
        self._device_id = value

    @property
    def countdown(self) -> Optional[int]:
        """Gets the countdown value.

        :return: The countdown value of the virtual device.
        :rtype: Optional[int]
        """
        return self._countdown

    @countdown.setter
    def countdown(self, value: Optional[int]) -> None:
        """Sets the countdown value.

        :param value: The countdown value to set.
        :type value: Optional[int]
        """
        self._countdown = value

    def trigger_get_state(
        self, mqtt_service: IMQTTService, device_id: str = None
    ) -> None:
        """Triggers a state request to the device.

        :param mqtt_service: The client instance used for communication.
        :type mqtt_service: IMQTTService
        :param device_id: Optional device ID to retrieve state for, defaults to None.
        :type device_id: str, optional
        :raises TypeError: If mqtt_service is not an instance of MQTTService.
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be instance of MQTTService, not {type(mqtt_service)}"
            )
        _encoder = self._encoder
        _state_request = _encoder.get_state_request(device_id)
        if _state_request is None:
            iotlib_logger.debug("%s : unable to get state")
        else:
            _state_topic, _state_payload = _state_request
            mqtt_service.mqtt_client.publish(_state_topic, _state_payload)

    def trigger_change_state(
        self, mqtt_service: IMQTTService, is_on: bool, on_time: int | None = None
    ) -> None:
        """
        Triggers a change in the state of a device.

        This method sends a request message to the device to change the current state of the device.

        :param mqtt_service: The client instance used for communication.
        :type mqtt_service: IMQTTService
        :param is_on: The new state of the device (True for ON, False for OFF).
        :type is_on: bool
        :param on_time: The duration for which the device should remain ON, in seconds.
            If None, the device will remain ON indefinitely, defaults to None.
        :type on_time: int | None, optional
        :raises TypeError: If mqtt_service is not an instance of MQTTService.
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be instance of MQTTService, not {type(mqtt_service)}"
            )
        _encoder = self._encoder

        if _encoder.is_pulse_request_allowed():
            iotlib_logger.debug(
                "[%s] Pulse request allowed -> change state with on_time : %s",
                self,
                on_time,
            )
            _state_request = _encoder.change_state_request(
                is_on, device_id=self.device_id, on_time=on_time
            )
        else:
            iotlib_logger.debug("[%s] Pulse request not allowed -> change state", self)
            _state_request = _encoder.change_state_request(
                is_on, device_id=self.device_id
            )
            if on_time is not None:
                iotlib_logger.debug(
                    "[%s] Stop it later with on_time : %s", self, on_time
                )
                self._stop_later(on_time, mqtt_service)

        if _state_request is None:
            iotlib_logger.warning("%s : unable to change state")
        else:
            _state_topic, _state_payload = _state_request
            _info = mqtt_service.mqtt_client.publish(
                _state_topic, _state_payload, qos=2, retain=False
            )
            iotlib_logger.debug(
                "Publishing to topic %s : %s - rc : %s - mid : %s",
                _state_topic,
                _state_payload,
                _info.rc,
                _info.mid,
            )

    def _stop_later(self, when: int, mqtt_service: IMQTTService) -> None:
        iotlib_logger.debug('[%s] Automatially stop after "%s" sec.', self, when)
        if not isinstance(when, int) or when <= 0:
            raise TypeError(
                f'Expecting a positive int for period "{when}", not {type(when)}'
            )
        if self._stop_timer:
            self._stop_timer.cancel()  # a timer is allready set, cancel it
        self._stop_timer = threading.Timer(when, self.trigger_stop, [mqtt_service])
        self._stop_timer.start()

    def trigger_start(
        self, mqtt_service: IMQTTService, on_time: Optional[int] = None
    ) -> bool:
        """
        Ask the device to start.

        This method triggers the device to start. If the device is already in the "on" state,
        no action is required and the method returns False. Otherwise, the method requests
        the device to turn on by calling the `trigger_change_state` method with the `is_on`
        parameter set to True.

        :param mqtt_service: The client object used to communicate with the device.
        :type mqtt_service: IMQTTService
        :param on_time: The time duration for which the device should remain on.
            If None, the device will remain ON indefinitely, defaults to None.
        :type on_time: int | None, optional
        :return: Returns True if the switch state is OFF when the method is called.
        :rtype: bool
        :raises TypeError: If mqtt_service is not an instance of MQTTService.
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be instance of MQTTService, not {type(mqtt_service)}"
            )
        if self.value:
            iotlib_logger.debug('[%s] is already "on" -> no action required', self)
            return False
        iotlib_logger.debug('[%s] is "off" -> request to turn it "on"', self)
        self.trigger_change_state(
            mqtt_service=mqtt_service,
            is_on=True,
            on_time=on_time if on_time is not None else self.countdown,
        )
        return True

    def trigger_stop(self, mqtt_service: IMQTTService) -> bool:
        """
        Ask the device to stop.

        This method is used to send a request to the device to stop its operation.
        If the switch state is currently ON, it will send a request to turn it OFF via MQTT.

        :param mqtt_service: The client object used to communicate with the device.
        :type mqtt_service: IMQTTService
        :return: Returns True if the switch state is ON when the method is called, indicating
            that a request to turn it OFF has been sent.
        :rtype: bool
        :raises TypeError: If mqtt_service is not an instance of MQTTService.
        """
        if not isinstance(mqtt_service, IMQTTService):
            raise TypeError(
                f"mqtt_service must be instance of MQTTService, not {type(mqtt_service)}"
            )
        iotlib_logger.debug("[%s] stop switch and reset stop timer", self)
        self._stop_timer = None

        if not self.value:
            iotlib_logger.debug(
                '\t > [%s] is already "off" -> no action required', self
            )
            return False

        iotlib_logger.debug(
            '\t > [%s] is "on" -> request to turn it "off" via MQTT', self
        )
        self.trigger_change_state(mqtt_service=mqtt_service, is_on=False, on_time=None)
        return True


class Melodies(enum.IntEnum):
    """
    Enumeration of melodies available for virtual devices.
    """

    MELO_01 = 1
    DING_DONG1 = 2
    DING_DONG2 = 3
    MELO_04 = 4
    MELO_05 = 5
    FIRE = 6
    HORN = 7
    MELO_08 = 8
    MELO_09 = 9
    DOG = 10
    AMBULANCE = 11
    DING_DONG3 = 12
    PHONE = 13
    MELO_14 = 14
    MELO_15 = 15
    WAKE_UP1 = 16
    WAKE_UP2 = 17
    DING_DONG4 = 18


class Level(enum.Enum):
    """
    Represents the level of alarm.

    The `Level` class is an enumeration that defines three levels: LOW, MEDIUM, and HIGH.
    Each level is associated with a string value.

    :cvar LOW: Represents a low level of alarm.
    :cvar MEDIUM: Represents a medium level of alarm.
    :cvar HIGH: Represents a high level of alarm.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Alarm(Operable):
    """Implementation of a virtual Alarm."""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.ALARM_PROPERTY


class Switch(Operable):
    """Implementation of a virtual Switch"""

    def __init__(self, *argc, **kwargs) -> None:
        """
        Initializes a new instance of the Switch class.

        This method initializes a new instance of the Switch class with a given friendly
        name and a quiet mode flag.

        :param argc: Variable length argument list.
        :param kwargs: Arbitrary keyword arguments. Expected keys are:
            - friendly_name (str): The friendly name of the switch. Defaults to "".
            - quiet_mode (bool): A flag indicating whether the switch is in quiet mode.
            Defaults to False.
        """
        super().__init__(*argc, **kwargs)
        self._device_id = None  # Relay numbers of multi-channel devices

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.SWITCH_PROPERTY


class Switch0(Switch):
    """Virtual switch #0 of a multi channel device"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_id = 0

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.SWITCH0_PROPERTY


class Switch1(Switch):
    """Virtual switch #1 of a multi channel device"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_id = 1

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.SWITCH1_PROPERTY


class Sensor(VirtualDevice):
    """Sensor virtual devices

    This virtual sensor device manages sensor values that can be
    read by observer devices.

    """

    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name, quiet_mode=quiet_mode)
        self._sensor_observers: list[Operable] = []

    def get_sensor_observers(self) -> list[VirtualDevice]:
        """
        Get the list of observer devices.

        This method returns the list of Operable device objects that are observing the sensor
        values.

        :return: The list of Operable device objects that are observing the sensor values.
        :rtype: list[VirtualDevice]
        """
        return self._sensor_observers

    def add_observer(self, device: Operable) -> None:
        """Add an observer device to be notified of sensor value changes.

        This method adds an Operable device to the list of observer devices.

        :param device: The Operable device to be added as an observer.
        :type device: Operable
        """
        if not isinstance(device, Operable):
            raise TypeError(f"Device must be instance of Operable, not {type(device)}")
        self._sensor_observers.append(device)


class TemperatureSensor(Sensor):
    """Temperature sensor"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.TEMPERATURE_PROPERTY

    def handle_value(self, value: float) -> list:
        # Implement the abstract method from AbstractDevice class
        return super().handle_value(round(float(value), 1))


class HumiditySensor(Sensor):
    """Humidity sensor"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.HUMIDITY_PROPERTY


class LightSensor(Sensor):
    """Light sensor"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.LIGHT_PROPERTY


class ConductivitySensor(Sensor):
    """Conductivity sensor"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.CONDUCTIVITY_PROPERTY


class Button(Sensor):
    """Button managing 3 types of messages : single, double and long button press"""

    def __init__(self, friendly_name=None):
        super().__init__(friendly_name, quiet_mode=False)

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.BUTTON_PROPERTY

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: str):
        # Handle button action
        _accepted_values = [
            ButtonValues.SINGLE_ACTION.value,
            ButtonValues.DOUBLE_ACTION.value,
            ButtonValues.LONG_ACTION.value,
            ButtonValues.OFF.value,
        ]
        if value is None:
            # Discard value if None
            return
        if value not in _accepted_values:
            # Validate value type
            raise ValueError(
                f'Button value "{value}" is invalid, must be in  list : "{_accepted_values}"'
            )
        if not isinstance(value, str):
            raise TypeError(f"Value {value} is not of type string")
        # else:
        self._value = value


class Motion(Sensor):
    """Virtual button manager"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.MOTION_PROPERTY


class ADC(Sensor):
    """Analog-to-digital converter"""

    def get_property(self) -> str:
        # Returns the property of the virtual device.
        return PropertyConfig.ADC_PROPERTY

    def handle_value(self, value: float) -> list:
        # Implement the abstract method from AbstractDevice class
        return super().handle_value(round(float(value), 1))
