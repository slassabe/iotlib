#!/usr/local/bin/python3
# coding=utf-8
''' Zigbee2mqtt bridge and implementation devices
'''
import json
from json.decoder import JSONDecodeError
from abc import abstractmethod, ABCMeta
from typing import Optional

# Non standard lib
from iotlib.utils import iotlib_logger
from iotlib.abstracts import AbstractEncoder
from iotlib.codec.core import Codec, DecodingException
from iotlib.codec.config import BaseTopic
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               Switch0, Switch1, TemperatureSensor)


# Zigbee devices
# Buttons
BUTTON_SINGLE_ACTION = 'single'
BUTTON_DOUBLE_ACTION = 'double'
BUTTON_LONG_ACTION = 'long'
# Switch
SWITCH_POWER = 'state'
SWITCH0_POWER = 'state_right'
SWITCH1_POWER = 'state_left'
# Switch state values
STATE_ON = 'ON'
STATE_OFF = 'OFF'


def get_root_topic(device_name: str, base_topic: str) -> str:
    ''' Return the Z2M root topic for a device
    '''
    return f'{base_topic}/{device_name}'


def get_availability_topic(device_name: str, base_topic: str) -> str:
    ''' Return the Z2M availability topic for a device
    '''
    return f'{base_topic}/{device_name}/availability'


class DeviceOnZigbee2MQTT(Codec):
    ''' Root bridge between Zigbee devices (connected via Zigbee2MQTT) and MQTT Clients
    '''

    def __init__(self,
                 device_name: str,
                 base_topic: Optional[str] = None):
        '''Subscribes on Zigbee2mqtt topics to receive information from devices :
        * zigbee2mqtt/<name>/             : to get device attributs
        * zigbee2mqtt/<name>/availability : to get device availability, not a Zigbee attribut

        Args:
            device_name (str): the device name to subscribe
        '''
        # Topics to subscribe to
        base_topic = base_topic or BaseTopic.Z2M_BASE_TOPIC.value
        assert isinstance(device_name, str), \
            f'Bad value for device_name : {device_name} of type {type(device_name)}'
        super().__init__(device_name, base_topic)

        self._root_topic = get_root_topic(device_name, base_topic)
        self._availability_topic = get_availability_topic(
            device_name, base_topic)

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

        if payload not in ['online', 'offline', None]:
            raise DecodingException(f'Payload value error: {payload}')
        else:
            return payload == 'online'

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
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: str = None,
                 v_temp: Optional[TemperatureSensor] = None,
                 v_humi: Optional[HumiditySensor] = None) -> None:
        """
        Initialize the object.

        Args:
            device_name (str): The name of the device.
            v_temp (TemperatureSensor, optional): The temperature sensor.
            v_humi (HumiditySensor, optional): The humidity sensor.
            topic_base (str, optional): The base topic.
        """
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_temp = v_temp or TemperatureSensor(friendly_name)
        assert isinstance(v_temp, TemperatureSensor), \
            f'Bad value : {v_temp} of type {type(v_temp)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_temp_pl,
                                  v_temp)

        v_humi = v_humi or HumiditySensor(friendly_name)
        assert isinstance(v_humi, HumiditySensor), \
            f'Bad value : {v_humi} of type {type(v_humi)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_humi_pl,
                                  v_humi)

    def _decode_temp_pl(self, _topic, payload: dict) -> float:
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
            raise DecodingException(
                f'No "soil_moisture" key in payload : {payload}')
        else:
            return int(_value)


class ButtonOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    ''' Bridge between Wireless button devices and MQTT Clients '''

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_button: Optional[Button] = None) -> None:
        """
        Initialize the object.

        Args:
            device_name (str): The name of the device.
            v_button (Button, optional): The button. Defaults to None.
            topic_base (str, optional): The base topic. Defaults to None.
        """
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_button = v_button or Button(friendly_name)
        assert isinstance(v_button, Button), \
            f'Bad value : {v_button} of type {type(v_button)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_value_pl,
                                  v_button)

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> str:
        raise NotImplementedError


class SonoffSnzb01(ButtonOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/SNZB-01.html#sonoff-snzb-01 '''

    def _decode_value_pl(self, topic, payload) -> str:
        _pl = payload.get('action')
        action_map = {
            'single': BUTTON_SINGLE_ACTION,
            'double': BUTTON_DOUBLE_ACTION,
            'long': BUTTON_LONG_ACTION
        }
        if _pl in action_map:
            return action_map[_pl]
        raise DecodingException(
            f'Received erroneous Action value : "{_pl}"')


class MotionOnZigbee(DeviceOnZigbee2MQTT, metaclass=ABCMeta):
    '''  Bridge between MOTION SENSOR devices and MQTT Clients '''

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_motion: Optional[Motion] = None) -> None:
        """
        Initialize the object.

        Args:
            device_name (str): The name of the device.
            v_motion (Motion, optional): The motion sensor. Defaults to None.
            topic_base (str, optional): The base topic. Defaults to None.
        """
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_motion = v_motion or Motion(friendly_name)
        assert isinstance(v_motion, Motion), \
            f'Bad value : {v_motion} of type {type(v_motion)}'
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_value_pl,
                                  v_motion)

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> dict:
        raise NotImplementedError


class SonoffSnzb3(MotionOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/SNZB-03.html#sonoff-snzb-03 '''

    def _decode_value_pl(self, topic, payload) -> bool:
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
                 encoder: AbstractEncoder,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_alarm: Optional[Alarm] = None) -> None:
        """
        Initialize the object.

        Args:
            device_name (str): The name of the device.
            v_alarm (Alarm, optional): The alarm. Defaults to None.
            topic_base (str, optional): The base topic. Defaults to None.
        """
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_alarm = v_alarm or Alarm(friendly_name)
        if not isinstance(encoder, AbstractEncoder):
            raise ValueError(f'Bad value : {encoder} of type {type(encoder)}')
        if not isinstance(v_alarm, Alarm):
            raise ValueError(f'Bad value : {v_alarm} of type {type(v_alarm)}')
        v_alarm.set_encoder(encoder)

        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_value_pl,
                                  v_alarm)

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> bool:
        """Decode state payload."""
        raise NotImplementedError


class NeoNasAB02B2(AlarmOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html '''
    _key_alarm = 'alarm'

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_alarm: Optional[Alarm] = None) -> None:
        super().__init__(NeoNasAB02B2Encoder(get_root_topic(device_name, topic_base)),
                         device_name=device_name,
                         friendly_name=friendly_name,
                         topic_base=topic_base,
                         v_alarm=v_alarm)

    def _decode_value_pl(self, topic, payload) -> bool:
        _pl = payload.get(self._key_alarm)
        if not isinstance(_pl, bool):
            raise DecodingException(
                f'Received erroneous payload : "{payload}"')
        return _pl


class NeoNasAB02B2Encoder(AbstractEncoder):
    _key_alarm = 'alarm'
    _key_melody = 'melody'
    _key_alarm_level = 'volume'
    _key_alarm_duration = 'duration'

    def __init__(self, root_topic) -> None:
        self._root_topic = root_topic
        self._melody = 1
        self._alarm_level = 'low'

    def set_sound(self,
                  melody: int,
                  alarm_level: str) -> None:
        """Change the alarm parameters.

        Args:
            melody (int): The alarm melody number.
            alarm_level (str): The alarm volume level.

        """
        assert isinstance(melody, int) and melody in range(1, 19), \
            f'Bad value for melody : {melody}'
        assert isinstance(alarm_level, str) and alarm_level in ['low', 'medium', 'high'], \
            f'Bad value for alarm_level : {alarm_level}'

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        return None

    def is_pulse_request_allowed(self, device_id: Optional[int]) -> bool:
        return True

    def change_state_request(self,
                             is_on: bool,
                             device_id: Optional[int] = None,
                             on_time: Optional[int] = None) -> tuple[str, str]:
        _set = {self._key_alarm: is_on,
                self._key_melody: self._melody,
                self._key_alarm_level: self._alarm_level,
                self._key_alarm_duration: on_time,
                }
        iotlib_logger.debug('Encode payload : %s', _set)
        return f'{self._root_topic}/set', json.dumps(_set)


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
                 encoder: AbstractEncoder,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_switch: Optional[Switch] = None,
                 ) -> None:
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_switch = v_switch or Switch(friendly_name)
        if not isinstance(encoder, AbstractEncoder):
            raise ValueError(
                f'Encoder must be an instance of AbstractEncoder, not {type(encoder)}')
        if not isinstance(v_switch, Switch):
            raise ValueError(
                f'v_switch must be an instance of Switch, not {type(v_switch)}')
        # self._v_switch = v_switch
        v_switch.set_encoder(encoder)

        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_value_pl,
                                  v_switch)
        # self.ask_for_state()
        iotlib_logger.warning('%s : unable to ask state', self)

    def _decode_value_pl(self, topic, payload) -> bool:
        raise NotImplementedError


class SonoffZbminiL(SwitchOnZigbee):
    ''' Bridge for Sonoff ZBMINI-L devices.
     https://www.zigbee2mqtt.io/devices/ZBMINI-L.html#sonoff-zbmini-l 
     '''

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: Optional[str] = None,
                 v_switch: Optional[Switch] = None,) -> None:
        super().__init__(SonoffZbminiLEncoder(get_root_topic(device_name, topic_base)),
                         device_name=device_name,
                         friendly_name=friendly_name,
                         topic_base=topic_base,
                         v_switch=v_switch)

    def _decode_value_pl(self, topic, payload) -> bool:
        _pl = payload.get(SWITCH_POWER)
        if _pl == STATE_ON:
            return True
        elif _pl == STATE_OFF:
            return False
        else:
            raise DecodingException(
                f'Received erroneous State value : "{_pl}"')


class SonoffZbminiLEncoder(AbstractEncoder):
    def __init__(self, root_topic: str) -> None:
        self._root_topic = root_topic

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        return f'{self._root_topic}/get', '{"state":""}'

    def is_pulse_request_allowed(self, device_id: Optional[int]) -> bool:
        return True

    def change_state_request(self,
                             is_on: bool,
                             device_id: Optional[int] = None,
                             on_time: Optional[str] = None) -> tuple[str, str]:
        """
        Constructs a change state request for the device.

        Args:
            is_on (bool): Indicates whether the device should be turned on or off.
            device_id (int | None): The ID of the device. If None, the request is for all devices.
            on_time (int | None): The duration in seconds for which the device should remain on. If None, the device will stay on indefinitely.

        Returns:
            tuple[str, str]: A tuple containing the MQTT topic and the payload in JSON format.
        """
        _topic = f'{self._root_topic}/set'
        _payload = {SWITCH_POWER: STATE_ON if is_on else STATE_OFF}
        if on_time is not None:
            _payload["on_time"] = on_time
        return _topic, json.dumps(_payload)


class MultiSwitchOnZigbee(DeviceOnZigbee2MQTT):
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
                 encoder: AbstractEncoder,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: str = None,
                 v_switch0: Optional[Switch0] = None,
                 v_switch1: Optional[Switch1] = None,
                 ) -> None:
        super().__init__(device_name, topic_base)

        friendly_name = friendly_name or device_name
        v_switch0 = v_switch0 or Switch(friendly_name)
        v_switch1 = v_switch1 or Switch(friendly_name)
        if not isinstance(encoder, AbstractEncoder):
            raise ValueError(f'Bad value : {encoder} of type {type(encoder)}')
        if not isinstance(v_switch0, Switch0):
            raise ValueError(
                f'Bad value : {v_switch0} of type {type(v_switch0)}')
        if not isinstance(v_switch1, Switch1):
            raise ValueError(
                f'Bad value : {v_switch1} of type {type(v_switch1)}')
        v_switch0.set_encoder(encoder)
        # self._v_switch0 = v_switch0
        v_switch1.set_encoder(encoder)
        # self._v_switch1 = v_switch1

        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_switch0_value_pl,
                                  v_switch0)
        self._set_message_handler(self._root_topic,
                                  self.__class__._decode_switch1_value_pl,
                                  v_switch1)
        # self.ask_for_state()
        iotlib_logger.warning('%s : unable to ask state', self)

    def _decode_switch0_value_pl(self, topic, payload) -> bool:
        raise NotImplementedError

    def _decode_switch1_value_pl(self, topic, payload) -> bool:
        raise NotImplementedError


class TuYaTS0002(MultiSwitchOnZigbee):
    ''' https://www.zigbee2mqtt.io/devices/TS0002.html '''

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 topic_base: str = None,
                 v_switch0: Optional[Switch0] = None,
                 v_switch1: Optional[Switch1] = None,
                 ) -> None:

        super().__init__(TuYaTS0002Encoder(get_root_topic(device_name, topic_base)),
                         device_name,
                         friendly_name=friendly_name,
                         topic_base=topic_base,
                         v_switch0=v_switch0,
                         v_switch1=v_switch1)

    def _decode_switch_value_pl(self, topic, payload, switch_power) -> bool | None:
        """
        Decode the switch value from the payload.

        Args:
            topic (str): The topic of the message.
            payload (str): The payload of the message.
            switch_power (str): The switch power identifier.

        Returns:
            bool | None: The decoded switch value. Returns True if the switch is on,
            False if the switch is off, and None if the switch identifier is invalid.

        Raises:
            DecodingException: If the state value or switch identifier is erroneous.
        """
        _json_pl = json.loads(payload)
        _the_switch = next(iter(_json_pl))
        if _the_switch == switch_power:
            _pl = _json_pl.get(switch_power)
            if _pl == STATE_ON:
                return True
            elif _pl == STATE_OFF:
                return False
            else:
                raise DecodingException(
                    f'Received erroneous State value : "{_pl}"')
        elif _the_switch in [SWITCH0_POWER, SWITCH1_POWER]:
            return None
        else:
            raise DecodingException(
                f'Received erroneous Switch identifier : "{_the_switch}"')

    def _decode_switch0_value_pl(self, topic, payload) -> bool | None:
        return self._decode_switch_value_pl(topic, payload, SWITCH0_POWER)

    def _decode_switch1_value_pl(self, topic, payload) -> bool | None:
        return self._decode_switch_value_pl(topic, payload, SWITCH1_POWER)


class TuYaTS0002Encoder(AbstractEncoder):
    def __init__(self, root_topic: str) -> None:
        self._root_topic = root_topic

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        return f'{self._root_topic}/get', '{"state_left":"","state_right":""}'

    def is_pulse_request_allowed(self, device_id: Optional[int]) -> bool:
        return True

    def change_state_request(self,
                             is_on: bool,
                             device_id: Optional[int] = None,
                             on_time: Optional[int] = None) -> tuple[str, str]:
        """
        Constructs a change state request for the device.

        Args:
            is_on (bool): Indicates whether the device should be turned on or off.
            device_id (int | None): The ID of the device. If None, the request is for all devices.
            on_time (int | None): The duration in seconds for which the device should remain on. If None, the device will stay on indefinitely.

        Returns:
            tuple[str, str]: A tuple containing the MQTT topic and the payload in JSON format.
        """
        if device_id is None:
            _key_power = SWITCH_POWER
        elif device_id == 0:
            _key_power = SWITCH0_POWER
        elif device_id == 1:
            _key_power = SWITCH1_POWER
        else:
            raise ValueError(f'Bad value for device_id : {device_id}')

        _topic = f'{self._root_topic}/set'
        _payload = {_key_power: STATE_ON if is_on else STATE_OFF}
        if on_time is not None:
            _payload["on_time"] = on_time
        return _topic, json.dumps(_payload)
