#!/usr/local/bin/python3
# coding=utf-8

import enum
import threading
from abc import abstractmethod

from iotlib.abstracts import (
    AbstractDevice, Surrogate, ResultType, VirtualDeviceProcessor)
from iotlib.devconfig import PropertyConfig, ButtonValues

from . import package_level_logger


class VirtualDevice(AbstractDevice):
    """VirtualDevice is the base class for all virtual devices.

    It contains common attributes and methods for virtual devices like:

    - friendly_name: Name of the device
    - registered_list: List of devices registered to events

    Main methods:

    - __init__() : Constructor
    - __repr__() : Representation for debug/logging
    - __str__() : String representation 
    - registers() : Register a device to events
    - process_value() : Processes a value, must be implemented in child classes
    - _on_event() : Called on event, to be implemented in child classes

    The class allows to create virtual representations of physical devices
    like sensors, switches etc. and attach callbacks and logic to them.

    Child classes will implement device specific logic and processing.
    """

    _logger = package_level_logger

    def __init__(self, friendly_name: str, quiet_mode: bool) -> None:
        self.friendly_name = friendly_name
        self._value = None
        self._quiet_mode = quiet_mode
        self._processor_list: list[VirtualDeviceProcessor] = []

    def __repr__(self):
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({_res})'

    def __str__(self):
        return f'{self.__class__.__name__} ({self.friendly_name})'

    @property
    def value(self):
        return self._value

    def _validate_value_type(self, value: any):
        _property = self.get_property()
        _type_cast = self.get_property().property_type
        if not isinstance(value, _type_cast):
            raise TypeError(
                f"Value {value} is not of type {_type_cast} for property {_property}")

    @value.setter
    def value(self, value):
        self._validate_value_type(value)
        self._value = value

    def handle_value(self, value, bridge: Surrogate) -> ResultType:
        if value is None:
            # No relevant value received (can be info on device like battery level), ignore
            return ResultType.IGNORE
        elif (self.value == value) and self._quiet_mode:
            return ResultType.ECHO
        else:
            self.value = value
            for _processor in self._processor_list:
                self._logger.debug('Execute processor : %s', _processor)
                _processor.process_value_update(self, bridge)
            return ResultType.SUCCESS

    def processor_append(self, processor: VirtualDeviceProcessor) -> None:
        if not isinstance(processor, VirtualDeviceProcessor):
            raise TypeError(
                f"Processor must be instance of Processor, not {type(processor)}")
        self._processor_list.append(processor)

    @abstractmethod
    def get_property(self) -> str:
        raise NotImplementedError


class Operable(VirtualDevice):
    """ Root implementation of a virtual Operable device (Switch or Alarm)
    """

    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Used by Shelly : relay numbers
        self._stop_timer = None
        self._pulse_instruction_allowed = False

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, value):
        self._device_id = value

    @property
    def pulse_is_allowed(self):
        return self._pulse_instruction_allowed

    @pulse_is_allowed.setter
    def pulse_is_allowed(self, value):
        self._pulse_instruction_allowed = value

    def trigger_get_state(self,
                          bridge: Surrogate,
                          device_id=None) -> None:
        """Triggers a state request to the device bridge.

        Sends a request message to the device bridge to retrieve the 
        current state of the device. The device bridge will publish 
        a state update message in response.

        Args:
        bridge: The device bridge instance.
        device_id: Optional device ID to retrieve state for.
        """
        _request = bridge.codec.get_state_request(device_id)
        if _request is None:
            self._logger.debug('%s : unable to get state')
        else:
            _topic, _payload = _request
            bridge.publish_message(_topic, _payload)

    def trigger_change_state(self,
                             bridge: Surrogate,
                             is_on: bool,
                             device_id=None) -> None:
        _request = bridge.codec.change_state_request(is_on, device_id)
        if _request is None:
            self._logger.debug('%s : unable to change state')
        else:
            _topic, _payload = _request
            bridge.publish_message(_topic, _payload)

    def trigger_start(self, bridge: Surrogate) -> bool:
        ''' Ask the device to start

        Returns:
            bool: returns True if switch state is OFF when method called      
        '''
        if self.value:
            self._logger.debug('[%s] is already "on" -> no action required',
                               self)
            return False
        self._logger.debug('[%s] is "off" -> request to turn it "on"', self)
        self.trigger_change_state(bridge,
                                  is_on=True,
                                  device_id=self._device_id)
        return True

    def trigger_stop(self, bridge: Surrogate) -> bool:
        ''' Ask the device to stop

        Returns:
            bool: returns True if switch state is ON  when method called    
        '''
        self._logger.debug('[%s] stop switch and reset stop timer', self)
        self._stop_timer = None

        if not self.value:
            self._logger.debug('\t > [%s] is already "off" -> no action required',
                               self)
            return False
        else:
            self._logger.debug('\t > [%s] is "on" -> request to turn it "off" via MQTT',
                               self)
            self.trigger_change_state(bridge,
                                      is_on=False,
                                      device_id=self._device_id)
            return True

    def _remember_to_turn_the_light_off(self, when: int, bridge) -> None:
        self._logger.debug('[%s] Automatially stop after "%s" sec.',
                           self,  when)
        if not isinstance(when, int):
            raise TypeError(
                f'Expecting type int for period "{when}", not {type(when)}')
        if self._stop_timer:
            self._stop_timer.cancel()    # a timer is allready set, cancel it
        self._stop_timer = threading.Timer(when, self.trigger_stop, [bridge])
        self._stop_timer.start()


class Melodies(enum.IntEnum):
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
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class Alarm(Operable):
    """ Basic implementation of a virtual Alarm 
    """

    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)

    def get_property(self) -> str:
        return PropertyConfig.ALARM_PROPERTY


class Switch(Operable):
    """ Basic implementation of a virtual Switch 
    """

    def __init__(self, friendly_name=None, quiet_mode=False, countdown=0):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Used by Shelly : relay numbers
        self._count_down = countdown

    def handle_value(self, value: bool, bridge) -> list:
        _result = super().handle_value(value, bridge)
        if self._count_down != 0:
            if value and not self._stop_timer:
                # Automatically turn the switch off when manually turned on
                self._remember_to_turn_the_light_off(self._count_down, bridge)
        return _result

    def get_property(self) -> str:
        return PropertyConfig.SWITCH_PROPERTY


class Switch0(Switch):
    """ Virtual switch #0 of a multi channel device
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_id = 0

    def get_property(self) -> str:
        return PropertyConfig.SWITCH0_PROPERTY


class Switch1(Switch):
    """ Virtual switch #1 of a multi channel device
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_id = 1

    def get_property(self) -> str:
        return PropertyConfig.SWITCH1_PROPERTY


class Sensor(VirtualDevice):
    """Sensor virtual devices

    This virtual sensor device manages sensor values that can be 
    read by observer devices. 

    """

    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._sensor_observers: list[Operable] = []

    def get_sensor_observers(self) -> list[VirtualDevice]:
        """Get the list of observer devices.

        Returns:
            list: The list of Operable device objects that are observing 
                the sensor values.
        """
        return self._sensor_observers

    def add_observer(self, device: Operable) -> None:
        """Add an observer device to be notified of sensor value changes.

        Args:
            device (Operable): The device to add as an observer. 
                Must be an instance of Operable.

        Raises:
            TypeError: If device is not an instance of Operable.

        """
        if not isinstance(device, Operable):
            raise TypeError(
                f"Device must be instance of Operable, not {type(device)}")
        self._sensor_observers.append(device)


class TemperatureSensor(Sensor):
    """ Temperature sensor
    """

    def get_property(self) -> str:
        return PropertyConfig.TEMPERATURE_PROPERTY

    def handle_value(self, value: float, bridge) -> list:
        return super().handle_value(round(float(value), 1), bridge)


class HumiditySensor(Sensor):
    """ Humidity sensor
    """

    def get_property(self) -> str:
        return PropertyConfig.HUMIDITY_PROPERTY


class LightSensor(Sensor):
    """ Light sensor
    """

    def get_property(self) -> str:
        return PropertyConfig.LIGHT_PROPERTY


class ConductivitySensor(Sensor):
    """ Conductivity sensor
    """

    def get_property(self) -> str:
        return PropertyConfig.CONDUCTIVITY_PROPERTY


class Button(Sensor):
    """ Button managing 3 types of messages : single, double and long button press
    """

    def __init__(self, friendly_name=None):
        super().__init__(friendly_name,
                         quiet_mode=False)

    def get_property(self) -> str:
        return PropertyConfig.BUTTON_PROPERTY

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: str):
        # Handle button action
        _accepted_values = [ButtonValues.SINGLE_ACTION.value,
                            ButtonValues.DOUBLE_ACTION.value,
                            ButtonValues.LONG_ACTION.value,
                            ButtonValues.OFF.value]
        if value is None:
            # Discard value if None
            return
        elif value not in _accepted_values:
            # Validate value type
            raise ValueError(
                f'Button value "{value}" is invalid, must be in  list : "{_accepted_values}"')
        elif not isinstance(value, str):
            raise TypeError(
                f"Value {value} is not of type string")
        else:
            self._value = value


class Motion(Sensor):
    """ Virtual button manager
    """

    def get_property(self) -> str:
        return PropertyConfig.MOTION_PROPERTY


class ADC(Sensor):
    """ Analog-to-digital converter
    """

    def get_property(self) -> str:
        return PropertyConfig.ADC_PROPERTY

    def handle_value(self, value: float, bridge) -> list:
        return super().handle_value(round(float(value), 1), bridge)
