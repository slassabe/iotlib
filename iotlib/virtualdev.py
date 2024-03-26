#!/usr/local/bin/python3
# coding=utf-8

import enum
import threading
from abc import abstractmethod

from iotlib.abstracts import (AbstractDevice, Surrogate, ResultType,
                              VirtualDeviceProcessor)
from iotlib.devconfig import PropertyConfig, ButtonValues

from iotlib.utils import iotlib_logger


class VirtualDevice(AbstractDevice):
    """
    Represents a virtual device.
    """

    def __init__(self, friendly_name: str, quiet_mode: bool) -> None:
        """
        Initializes a new instance of the VirtualDevice class.

        Args:
            friendly_name (str): The friendly name of the device.
            quiet_mode (bool): A flag indicating whether the device is in quiet mode.
        """
        if friendly_name is not None:
            assert isinstance(friendly_name, str), \
                f'Bad value for friendly_name : {friendly_name} of type {type(friendly_name)}'
        self.friendly_name = friendly_name
        self._value = None
        self._quiet_mode = quiet_mode
        # List of processors associated with this device
        self._processor_list: list[VirtualDeviceProcessor] = []

    def __repr__(self):
        _sep = ''
        _res = ''
        for _attr, _val in self.__dict__.items():
            _res += f'{_sep}{_attr} : {_val}'
            _sep = ' | '
        return f'{self.__class__.__name__} ({_res})'

    def __str__(self):
        return f'{self.__class__.__name__} ({self.friendly_name} | value: {self.value})'

    @property
    def value(self):
        """
        Gets the value of the device.

        Returns:
            any: The value of the device.
        """
        return self._value

    def _validate_value_type(self, value: any):
        _property = self.get_property()
        _type_cast = self.get_property().property_type
        if not isinstance(value, _type_cast):
            raise TypeError(
                f"Value {value} is not of type {_type_cast} for property {_property}")

    @value.setter
    def value(self, value):
        """
        Sets the value of the device.

        Args:
            value (any): The value to set.

        Raises:
            TypeError: If the value is not of the expected type.
        """
        self._validate_value_type(value)
        self._value = value

    def handle_value(self, value, bridge: Surrogate) -> ResultType:
        """
        Handles the received value and performs necessary actions.

        Args:
            value (any): The received value.
            bridge (Surrogate): The bridge object.

        Returns:
            ResultType: The result of handling the value.
        """
        if value is None:
            # No relevant value received (can be info on device like battery level), ignore
            return ResultType.IGNORE
        elif (self.value == value) and self._quiet_mode:
            return ResultType.ECHO
        else:
            self.value = value
            for _processor in self._processor_list:
                iotlib_logger.debug(
                    'Execute processor : %s', _processor)
                _processor.process_value_update(self, bridge)
            return ResultType.SUCCESS

    def processor_append(self, processor: VirtualDeviceProcessor) -> None:
        """
        Appends a processor to the device.

        Args:
            processor (VirtualDeviceProcessor): The processor to append.

        Raises:
            TypeError: If the processor is not an instance of VirtualDeviceProcessor.
        """
        if not isinstance(processor, VirtualDeviceProcessor):
            raise TypeError(
                f"Processor must be instance of Processor, not {type(processor)}")
        self._processor_list.append(processor)

    @abstractmethod
    def get_property(self) -> str:
        """
        Gets the property of the device.

        Returns:
            str: The property of the device.
        """
        raise NotImplementedError


class Operable(VirtualDevice):
    """ Root implementation of a virtual Operable device (Switch or Alarm)
    """

    def __init__(self, friendly_name: str = None, quiet_mode: bool = False):
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Used by Shelly : relay numbers
        self._stop_timer = None
        self._pulse_instruction_allowed = False

    @property
    def device_id(self) -> str:
        return self._device_id

    @device_id.setter
    def device_id(self, value: str) -> None:
        self._device_id = value

    @property
    def pulse_is_allowed(self) -> bool:
        return self._pulse_instruction_allowed

    @pulse_is_allowed.setter
    def pulse_is_allowed(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(
                f"Pulse instruction allowed flag must be a bool, not {type(value)}")
        self._pulse_instruction_allowed = value

    def trigger_get_state(self,
                          bridge: Surrogate,
                          device_id: str = None) -> None:
        """Triggers a state request to the device bridge.

        Sends a request message to the device bridge to retrieve the 
        current state of the device. The device bridge will publish 
        a state update message in response.

        Args:
        bridge: The device bridge instance.
        device_id: Optional device ID to retrieve state for.
        """
        _encoder = bridge.codec.get_encoder()
        _state_request = _encoder.get_state_request(device_id)
        if _state_request is None:
            iotlib_logger.debug('%s : unable to get state')
        else:
            _state_topic, _state_payload = _state_request
            bridge.publish_message(_state_topic, _state_payload)

    def trigger_change_state(self,
                             bridge: Surrogate,
                             is_on: bool,
                             on_time: int | None = None) -> None:
        """
        Triggers a change in the state of a device.

        Args:
            bridge (Surrogate): The bridge object used for communication.
            is_on (bool): The new state of the device (True for ON, False for OFF).
            on_time (int | None): The duration for which the device should remain ON, in seconds.
                If None, the device will remain ON indefinitely.

        Returns:
            None

        Raises:
            None

        """
        _encoder = bridge.codec.get_encoder()
        _state_request = _encoder.change_state_request(is_on,
                                                       device_id=self.device_id,
                                                       on_time=on_time)
        if _state_request is None:
            iotlib_logger.warning('%s : unable to change state')
        else:
            _state_topic, _state_payload = _state_request
            bridge.publish_message(_state_topic, _state_payload)

    def trigger_start(self,
                      bridge: Surrogate,
                      on_time: int | None = None) -> bool:
        ''' Ask the device to start

        This method triggers the device to start. If the device is already in the "on" state,
        no action is required and the method returns False. Otherwise, the method requests
        the device to turn on by calling the `trigger_change_state` method with the `is_on`
        parameter set to True.

        Args:
            bridge (Surrogate): The bridge object used to communicate with the device.
            on_time (int | None, optional): The time duration for which the device should
                remain on. Defaults to None.

        Returns:
            bool: Returns True if the switch state is OFF when the method is called.
        '''
        if self.value:
            iotlib_logger.debug('[%s] is already "on" -> no action required',
                                self)
            return False
        iotlib_logger.debug(
            '[%s] is "off" -> request to turn it "on"', self)
        self.trigger_change_state(bridge,
                                  is_on=True,
                                  on_time=on_time)
        return True

    def trigger_stop(self, bridge: Surrogate) -> bool:
        ''' Ask the device to stop

        This method is used to send a request to the device to stop its operation.
        If the switch state is currently ON, it will send a request to turn it OFF via MQTT.

        Args:
            bridge (Surrogate): The bridge object used to communicate with the device.

        Returns:
            bool: Returns True if the switch state is ON when the method is called, indicating 
               that a request to turn it OFF has been sent.

        '''
        iotlib_logger.debug(
            '[%s] stop switch and reset stop timer', self)
        self._stop_timer = None

        if not self.value:
            iotlib_logger.debug('\t > [%s] is already "off" -> no action required',
                                self)
            return False
        else:
            iotlib_logger.debug('\t > [%s] is "on" -> request to turn it "off" via MQTT',
                                self)
            self.trigger_change_state(bridge,
                                      is_on=False,
                                      on_time=None)
            return True

    def _remember_to_turn_the_light_off(self, when: int, bridge: Surrogate) -> None:
        iotlib_logger.debug('[%s] Automatially stop after "%s" sec.',
                            self,  when)
        if not isinstance(when, int) or when <= 0:
            raise TypeError(
                f'Expecting a positive int for period "{when}", not {type(when)}')
        if self._stop_timer:
            self._stop_timer.cancel()    # a timer is allready set, cancel it
        self._stop_timer = threading.Timer(when, self.trigger_stop, [bridge])
        self._stop_timer.start()


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
    """
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class Alarm(Operable):
    """ Basic implementation of a virtual Alarm 
    """

    def __init__(self, friendly_name=None, quiet_mode: bool = False) -> None:
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)

    def get_property(self) -> str:
        return PropertyConfig.ALARM_PROPERTY


class Switch(Operable):
    """ Basic implementation of a virtual Switch 
    """

    def __init__(self,
                 friendly_name=None,
                 quiet_mode: bool = False,
                 countdown: int = 0) -> None:
        """Initializes a new instance of the Switch class.

        Args:
            friendly_name (str): The friendly name of the switch. Defaults to "".
            quiet_mode (bool): A flag indicating whether the switch is in quiet mode. Defaults to False.
            countdown (int): The countdown timer for the switch. Defaults to 0.
        """
        super().__init__(friendly_name,
                         quiet_mode=quiet_mode)
        self._device_id = None  # Relay numbers of multi-channel devices
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
