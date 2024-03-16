#!/usr/local/bin/python3
# coding=utf-8
''' Zigbee2mqtt bridge and implementation devices
'''
import json
from json.decoder import JSONDecodeError
from abc import abstractmethod, ABCMeta

# Non standard lib
from iotlib import package_level_logger

from iotlib.codec.core import Codec, DecodingException
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               TemperatureSensor)

# Zigbee2mqtt base topics configuration :
Z2M_BASE_TOPIC = 'zigbee2mqtt'

# Zigbee devices
# Buttons
BUTTON_SINGLE_ACTION = 'single'
BUTTON_DOUBLE_ACTION = 'double'
BUTTON_LONG_ACTION = 'long'
# Switch
SWITCH_POWER = 'state'
SWITCH_POWER_RIGHT = 'state_right'
SWITCH_POWER_LEFT = 'state_left'   # Not ipmplelmented !
# Switch state values
STATE_ON = 'ON'
STATE_OFF = 'OFF'


class DeviceOnZigbee2MQTT(Codec):
    ''' Root bridge between Zigbee devices (connected via Zigbee2MQTT) and MQTT Clients
    '''
    _logger = package_level_logger

    def __init__(self,
                 device_name: str,
                 base_topic: str = None):
        '''Subscribes on Zigbee2mqtt topics to receive information from devices :
        * zigbee2mqtt/<name>/             : to get device attributs
        * zigbee2mqtt/<name>/availability : to get device availability, not a Zigbee attribut

        Args:
            device_name (str): the device name to subscribe
        '''
        # Topics to subscribe to
        base_topic = base_topic or Z2M_BASE_TOPIC
        super().__init__(device_name, base_topic)

        self._root_topic = f'{base_topic}/{device_name}'
        self._availability_topic = f'{base_topic}/{device_name}/availability'

        self._logger.debug('Z2M codec created for device %s', device_name)

    def get_availability_topic(self) -> str:
        """Return the availability topic the client must subscribe
        """
        return self._availability_topic

    def decode_avail_pl(self, payload: str) -> bool:
        # Z2M availability payload depends on its configuration in configuration.yaml :
        # advanced:
        #   legacy_availability_payload: true
        # Whether to use legacy mode for the availability message payload (default: true)
        # true = online/offline
        # false = {"state":"online"} / {"state":"offline"}

        if payload != 'online' and payload != 'offline' and payload is not None:
            raise DecodingException(f'Payload value error: {payload}')
        else:
            return payload == 'online'

    def get_state_request(self, device_id: int | None) -> tuple[str, str]:
        """Unable to get state by default"""
        return None
    
    def change_state_request(self, is_on: bool, device_id: int | None) -> tuple[str, str]:
        """Unable to change state by default"""
        return None

    @staticmethod
    def fit_payload(payload) -> str:
        """Adjust payload to be decoded, that is fit in string
        """
        try:
            return json.loads(payload)
        except JSONDecodeError as exp:
            raise DecodingException(
                f'Exception occured while decoding : "{payload}"') from exp


class SensorOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    ''' Bridge between SENSOR devices and MQTT Clients '''

    def __init__(self,
                 device_name: SystemError,
                 v_temp: TemperatureSensor,
                 v_humi: HumiditySensor,
                 topic_base: str = None) -> None:
        super().__init__(device_name, topic_base)

        assert issubclass(type(v_temp), TemperatureSensor), \
            f'Bad value : {v_temp} of type {type(v_temp)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_temp_pl,
                                  v_temp)
        assert issubclass(type(v_humi), HumiditySensor), \
            f'Bad value : {v_humi} of type {type(v_humi)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_humi_pl,
                                  v_humi)

    def _decode_temp_pl(self, topic, payload: dict) -> float:
        _value = payload.get('temperature')
        if _value is None:
            raise DecodingException(
                f'No "temperature" key in payload : {payload}')
        else:
            return float(_value)

    @abstractmethod
    def _decode_humi_pl(self, topic, payload) -> int:
        raise NotImplementedError


class SonoffSnzb02(SensorOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/SNZB-02.html#sonoff-snzb-02 '''

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = payload.get('humidity')
        if _value is None:
            raise DecodingException(
                f'No "humidity" key in payload : {payload}')
        else:
            return int(_value)


class Ts0601Soil(SensorOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/TS0601_soil.html '''

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = payload.get('soil_moisture')
        if _value is None:
            raise ValueError(f'No "soil_moisture" key in payload : {payload}')
        else:
            return int(_value)


class ButtonOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    ''' Bridge between Wireless button devices and MQTT Clients '''

    def __init__(self,
                 device_name: str,
                 v_button: Button,
                 topic_base: str = None) -> None:
        super().__init__(device_name, topic_base)

        assert issubclass(type(v_button), Button), \
            f'Bad value : {v_button} of type {type(v_button)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_action_pl,
                                  v_button)

    @abstractmethod
    def _decode_action_pl(self, topic, payload) -> str:
        raise NotImplementedError


class SonoffSnzb01(ButtonOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/SNZB-01.html#sonoff-snzb-01 '''

    def _decode_action_pl(self, topic, payload) -> str:
        _pl = payload.get('action')
        if _pl is None:
            return None
        elif _pl == 'single':
            return BUTTON_SINGLE_ACTION
        elif _pl == 'double':
            return BUTTON_DOUBLE_ACTION
        elif _pl == 'long':
            return BUTTON_LONG_ACTION
        else:
            raise DecodingException(
                f'Received erroneous Action value : "{_pl}"')


class MotionOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    '''  Bridge between MOTION SENSOR devices and MQTT Clients '''

    def __init__(self,
                 device_name: str,
                 v_motion: Motion,
                 topic_base: str = None) -> None:
        super().__init__(device_name, topic_base)

        assert issubclass(type(v_motion), Motion), \
            f'Bad value : {v_motion} of type {type(v_motion)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_motion_pl,
                                  v_motion)

    @abstractmethod
    def _decode_motion_pl(self, topic, payload) -> dict:
        raise NotImplementedError


class SonoffSnzb3(MotionOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/SNZB-03.html#sonoff-snzb-03 '''

    def _decode_motion_pl(self, topic, payload) -> bool:
        _value = payload.get('occupancy')
        if _value is None:
            raise DecodingException(
                f'No "occupancy" key in payload : {payload}')
        else:
            return _value


class AlarmOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    """Zigbee alarm device representation.

    Represents a Zigbee alarm device connected via zigbee2mqtt. 
    Extends DeviceOnZigbee2MQTT to handle alarm specific 
    functionality like changing the alarm state and parameters.

    Args:
        device_name (str): The name of the Zigbee alarm device.
        v_alarm (Alarm): The virtual alarm device to link to.

    """

    def __init__(self,
                 device_name: str,
                 v_alarm: Alarm,
                 topic_base: str = None) -> None:
        super().__init__(device_name, topic_base)

        assert issubclass(type(v_alarm), Alarm), \
            f'Bad value : {v_alarm} of type {type(v_alarm)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_state_pl,
                                  v_alarm)


    @abstractmethod
    def set_sound(self,
                  melody: int,
                  alarm_level: str,
                  alarm_duration: int) -> None:
        """Change the alarm parameters.

        Args:
            melody (int): The alarm melody number.
            alarm_level (str): The alarm volume level.
            alarm_duration (int): The alarm duration in seconds.

        """
        raise NotImplementedError

    def _decode_state_pl(self, topic, payload) -> bool:
        """Decode state payload."""
        raise NotImplementedError

class NeoNasAB02B2(AlarmOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html '''
    _key_alarm = 'alarm'
    _key_melody = 'melody'
    _key_alarm_level = 'volume'
    _key_alarm_duration = 'duration'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._melody = 1
        self._alarm_level = 'low'
        self._alarm_duration = 5

    def set_sound(self,
                  melody: int,
                  alarm_level: str,
                  alarm_duration: int) -> None:
        assert issubclass(type(melody), int) and melody in range(1, 19), \
            f'Bad value for melody : {melody}'
        assert issubclass(type(alarm_level), str) and alarm_level in ['low', 'medium', 'high'], \
            f'Bad value for alarm_level : {alarm_level}'
        assert issubclass(type(alarm_duration), int) and alarm_duration in range(1, 120), \
            f'Bad value for alarm_duration : {alarm_duration}'
        self._melody = melody
        self._alarm_level = alarm_level
        self._alarm_duration = alarm_duration

    def change_state_request(self, is_on: bool, device_id: int | None) -> tuple[str, str]:
        # _set = {self._key_alarm: STATE_ON if is_on else STATE_OFF,
        _set = {self._key_alarm: is_on,
                self._key_melody: self._melody,
                self._key_alarm_level: self._alarm_level,
                self._key_alarm_duration: self._alarm_duration,
                }
        self._logger.debug('Encode payload : %s', _set)
        return f'{self._root_topic}/set', json.dumps(_set)

    def _decode_state_pl(self, topic, payload) -> bool:
        _pl = payload.get(self._key_alarm)
        if not issubclass(type(_pl), bool):
            raise DecodingException(
                f'Received erroneous payload : "{payload}"')
        return _pl


class SwitchOnZigbee(DeviceOnZigbee2MQTT):
    ''' Bridge between SWITCH devices connected via Zigbee2MQTT and MQTT Clients

    Features
        * get and set "state" SWITCH standard attribut
        * manage a countdown to automatically close a SWITCH turned on
        * check periodically its state

    Bridge publishes on these topics to send messages to Switch devices
        zigbee2mqtt/<name>/get      : to refresh state attribut
        zigbee2mqtt/<name>/set      : to change state attribute

    '''

    def __init__(self,
                 device_name: str,
                 v_switch: Switch,
                 topic_base: str = None) -> None:
        super().__init__(device_name, topic_base)

        assert issubclass(type(v_switch), Switch), \
            f'Bad value : {v_switch} of type {type(v_switch)}'
        self._v_switch = v_switch

        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_state_pl,
                                  v_switch)
        #self.ask_for_state()
        self._logger.warning('%s : unable to ask state', self)


    def get_state_request(self, device_id: int | None) -> tuple[str, str]:
        return f'{self._root_topic}/get', '{"state":""}'

    def change_state_request(self, is_on: bool, device_id: int | None) -> tuple[str, str]:
        _set = {SWITCH_POWER: STATE_ON if is_on else STATE_OFF}
        return f'{self._root_topic}/set', json.dumps(_set)
    
    def _decode_state_pl(self, topic, payload) -> bool:
        raise NotImplementedError


class SonoffZbminiL(SwitchOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/ZBMINI-L.html#sonoff-zbmini-l '''
    def _decode_state_pl(self, topic, payload) -> bool:
        _pl = payload.get(SWITCH_POWER)
        if _pl == STATE_ON:
            return True
        elif _pl == STATE_OFF:
            return False
        else:
            raise DecodingException(
                f'Received erroneous State value : "{_pl}"')


class SonoffZbSw02Right(SonoffZbminiL):
    ''' https://www.zigbee2mqtt.io/devices/ZB-SW02.html '''
    # Left channel is not yet implemented !!!
    _key_power = SWITCH_POWER_RIGHT
