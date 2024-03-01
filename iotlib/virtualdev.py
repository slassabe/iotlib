#!/usr/local/bin/python3
# coding=utf-8

import enum
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable

from . import package_level_logger
from iotlib.processor import VirtualDeviceProcessor
from iotlib.devconfig import PropertyConfig, ButtonValues


class ResultType(enum.IntEnum):
    IGNORE = -1
    SUCCESS = 0
    ECHO = 1

class VirtualDevice(ABC):
    """VirtualDevice is the base class for all virtual devices.

    It contains common attributes and methods for virtual devices like:

    - friendly_name: Name of the device
    - concrete_device: The physical device associated 
    - registered_list: List of devices registered to events

    Main methods:

    - __init__() : Constructor
    - __repr__() : Representation for debug/logging
    - __str__() : String representation 
    - concrete_device : Property to get/set the physical device  
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
        self._quiet_mode = quiet_mode
        self._value = None
        self._processor_list:list[Callable[[VirtualDevice], None]] = []

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

    def _validate_value_type(self, value):
        # Validate value type
        _property = self.get_property()
        _type_cast = self.get_property().property_type
        if not isinstance(value, _type_cast):
            raise TypeError(
                f"Value {value} is not of type {_type_cast} for property {_property}")

    @value.setter
    def value(self, value):
        self._validate_value_type(value)
        self._value = value

    @abstractmethod
    def get_property(self) -> str:
        raise NotImplementedError

    def handle_new_value(self, value) -> ResultType:
        """Handles a new value received from device manager for the virtual device.

        Checks if the value should be ignored based on previous value and 
        quiet mode. If valid, sets the new value and calls the event handler.

        Args:
            value: The new value received.

        Returns:
            A tuple of (property name, property value).
            Returns None if the value should be ignored.

        """
        if value is None:
            # No relevant value received (can be info on device like battery level), ignore
            return ResultType.IGNORE
        elif (self.value == value) and self._quiet_mode:
            return ResultType.ECHO
        else:
            self.value = value
            for _processor in self._processor_list:
                _processor.handle_device_update(self)
            return ResultType.SUCCESS


    def processor_append(self, processor):
        """Appends a Processor to the processor list"""
        if not isinstance(processor, VirtualDeviceProcessor):
            raise TypeError(
                f"Processor must be instance of Processor, not {type(processor)}")
        self._processor_list.append(processor)

class Sensor(VirtualDevice):
    """Sensor virtual devices

    This virtual sensor device manages sensor values that can be 
    read by observer devices. 

    """
    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._sensor_observers: list[Operable] = []

    @property
    def sensor_observers(self) -> list[VirtualDevice]:
        """Get the list of observer devices.

        Returns:
            list: The list of Operable device objects that are observing 
                the sensor values.
        """
        return self._sensor_observers

    def add_observer(self, device) -> None:
        """Add an observer to be notified of sensor value changes.
        
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

    def handle_new_value(self, value: float) -> list:
        return super().handle_new_value(round(float(value), 1))


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
    def value(self, value:str):
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

    def handle_new_value(self, value: float) -> list:
        return super().handle_new_value(round(float(value), 1))


class Operable(VirtualDevice):
    """ Root implementation of a virtual Operable device (Switch or Alarm)
    """

    def __init__(self, friendly_name=None, quiet_mode=False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Used by Shelly : relay numbers
        self._concrete_device = None
        self._stop_timer = None
        self._pulse_instruction_allowed = False

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, value):
        self._device_id = value

    @property
    def concrete_device(self):
        return self._concrete_device

    @concrete_device.setter
    def concrete_device(self, value):
        if self._concrete_device is not None:
            raise ValueError(f'Virtual device {self} allready used')
        self._concrete_device = value

    @property
    def pulse_is_allowed(self):
        return self._pulse_instruction_allowed

    @pulse_is_allowed.setter
    def pulse_is_allowed(self, value):
        self._pulse_instruction_allowed = value

    def trigger_start(self) -> bool:
        ''' Ask the device to start

        Returns:
            bool: returns True if switch state is OFF when method called      
        '''
        if self.value:
            self._logger.debug('[%s] is already "on" -> no action required',
                               self)
            return False
        self._logger.debug('[%s] is "off" -> request to turn it "on"', self)
        if self._device_id is None:
            self.concrete_device.change_state(True)
        else:
            self.concrete_device.change_device_id_state(self._device_id, True)
        return True

    def trigger_stop(self) -> bool:
        ''' Ask the device to stop after a period

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
            if self._device_id is None:
                self.concrete_device.change_state(False)
            else:
                self.concrete_device.change_device_id_state(
                    self._device_id, False)
            return True

    def start_and_stop(self, period: int) -> None:
        """ Ask the device to start, then stop after a period

        Args:
            duration (int): duration before stop switch.
        """
        self._logger.debug('[%s] Start it for "%s" sec.', self, period)
        if not isinstance(period, int):
            raise TypeError(
                f'Expecting type int for period "{period}", not {type(period)}')
        if self.pulse_is_allowed:
            self._logger.debug('[%s] pulse instruction allowed', self)
            self.concrete_device.pulse(period)
            self.trigger_start()
        else:
            self._logger.debug('[%s] pulse instruction NOT allowed', self)
            self.trigger_start()
            self._remember_to_turn_the_light_off(period)

    def _remember_to_turn_the_light_off(self, when: int) -> None:
        self._logger.debug('[%s] Automatially stop after "%s" sec.',
                           self,  when)
        if not isinstance(when, int):
            raise TypeError(
                f'Expecting type int for period "{when}", not {type(when)}')
        if self._stop_timer:
            self._stop_timer.cancel()    # a timer is allready set, cancel it
        self._stop_timer = threading.Timer(when, self.trigger_stop, [])
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

    def configure_alarm(self,
                        melody: Melodies,
                        alarm_level: Level,
                        alarm_duration: int) -> None:  # pylint: disable=unused-argument
        """ Configure the alarm type, level and duration
        """
        if not isinstance(melody, Melodies):
            raise TypeError(f'Melody {melody} is invalid,'
                            'must be one of Melodies enum value')
        if not isinstance(alarm_level, Level):
            raise TypeError(
                f'Alarm level "{alarm_level}" is invalid,'
                'must be one of Level enum value')
        self._logger.info('[%s] melody : %s - alarm_level: %s - alarm_duration: %s',
                          self,
                          melody,
                          alarm_level,
                          alarm_duration,
                          )
        self.concrete_device.set_sound(
            melody.value, alarm_level.value, alarm_duration)


class Switch(Operable):
    """ Basic implementation of a virtual Switch 
    """
    def __init__(self, friendly_name=None, quiet_mode=False, countdown=0):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Used by Shelly : relay numbers
        self._count_down = countdown

    def handle_new_value(self, value: bool) -> list:
        _result = super().handle_new_value(value)
        if self._count_down != 0:
            if value and not self._stop_timer:
                # Automatically turn the switch off when manually turned on
                self._remember_to_turn_the_light_off(self._count_down)
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

