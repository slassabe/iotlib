#!/usr/local/bin/python3
# coding=utf-8
""" Zigbee2mqtt bridge and implementation devices
"""
import enum
import json
from abc import ABCMeta, abstractmethod
from json.decoder import JSONDecodeError
from typing import Optional

from iotlib.abstracts import IEncoder
from iotlib.codec.config import BaseTopic
from iotlib.codec.core import Codec, DecodingException
from iotlib.utils import iotlib_logger
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               Switch0, Switch1, TemperatureSensor)

# Zigbee devices
# Buttons
BUTTON_SINGLE_ACTION = "single"
BUTTON_DOUBLE_ACTION = "double"
BUTTON_LONG_ACTION = "long"
# Switch
SWITCH_POWER = "state"
SWITCH0_POWER = "state_right"
SWITCH1_POWER = "state_left"


def get_root_topic(device_name: str, base_topic: str) -> str:
    """
    Returns the Zigbee2MQTT root topic for a device.

    This function constructs and returns the root topic for a device in the Zigbee2MQTT protocol.
    If no base topic is provided, it defaults to the value of `BaseTopic.Z2M_BASE_TOPIC`.

    :param device_name: The name of the device.
    :type device_name: str
    :param base_topic: The base topic for MQTT communication. Defaults to `BaseTopic.Z2M_BASE_TOPIC` if not provided.
    :type base_topic: str
    :return: The root topic for the device.
    :rtype: str
    """

    base_topic = base_topic or BaseTopic.Z2M_BASE_TOPIC.value
    return f"{base_topic}/{device_name}"


class PowerState(enum.Enum):
    """Enumeration representing the power state of a Rasmota device.

    Attributes:
        ON: Device is powered on
        OFF: Device is powered off
    """

    ON = "ON"
    OFF = "OFF"


class Availability(enum.Enum):
    """
    Enumeration representing the availability of a Tasmota device.

    The `Availability` enumeration defines three possible states for the availability of a Rasmota device:
    - `ONLINE`: The device is online and available.
    - `OFFLINE`: The device is offline and unavailable.
    - `NONE`: The availability status is unknown or not applicable.
    """

    ONLINE = "online"
    OFFLINE = "offline"
    NONE = None


_AVAILABILITY_VALUES = [avail.value for avail in Availability]


class DecoderOnZigbee2MQTT(Codec):
    """
    Represents a device on the Zigbee2MQTT protocol.

    This class is a subclass of the `Codec` class and represents a device that communicates using the Zigbee2MQTT protocol.
    It provides methods for encoding and decoding MQTT messages specific to this protocol.

    :inherits: `Codec`
    """

    #    <base_topic>
    #    └── <device_name>                                     <== self._root_topic
    #        └── availability : "online" | "offline" | None    <== self._availability_topic

    def __init__(self,
                 device_name: str,
                 friendly_name: Optional[str] = None,
                 base_topic: Optional[str] = None):
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given device name and an optional
        base topic for MQTT communication.

        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name to be used for the device.
        :type friendly_name: str
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to None.
        :type base_topic: Optional[str]
        :raises TypeError: If device_name or friendly_name is not a string.
        """
        friendly_name = friendly_name or device_name
        if not isinstance(device_name, str):
            raise TypeError(
                f'"device_name" must be an instance of str, not {type(device_name)}'
            )
        if not isinstance(friendly_name, str):
            raise TypeError(
                f'"friendly_name" must be an instance of str, not {type(friendly_name)}'
            )

        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        _root_topic = get_root_topic(device_name, base_topic)
        self._root_topic = _root_topic
        self._availability_topic = f"{_root_topic}/availability"

    def get_availability_topic(self) -> str:
        # Implement abstract method
        return self._availability_topic

    def decode_avail_pl(self, payload: str) -> bool:
        # Z2M availability payload depends on its configuration in configuration.yaml :
        # advanced:
        #   legacy_availability_payload: true
        # Whether to use legacy mode for the availability message payload (default: true)
        # true = online/offline
        # false = {"state":"online"} / {"state":"offline"}

        if payload not in _AVAILABILITY_VALUES:
            if payload in ['{"state":"online"}', '{"state":"offline"}']:
                iotlib_logger.error(
                    "Z2M configuration error: set 'legacy_availability_payload' to true"
                )
            else:
                iotlib_logger.error(
                    "Z2M configuration error: unknown availability payload : %s",
                    payload,
                )
            raise DecodingException(f"Payload value error: {payload}")
        return payload == Availability.ONLINE.value

    @staticmethod
    def fit_payload(payload) -> str:
        """Adjust payload to be decoded, that is fit in string"""
        try:
            return json.loads(payload)
        except JSONDecodeError as exp:
            raise DecodingException(
                f'Exception occured while decoding : "{payload}"'
            ) from exp


class SensorOnZigbee(DecoderOnZigbee2MQTT, metaclass=ABCMeta):
    """Bridge between SENSOR devices and MQTT Clients"""

    #    <base_topic>
    #    └── <device_name> : <json_payload>      <== self._root_topic
    #
    # JSON payload example :
    #    {"battery": Float,       <- dismiss
    #     "humidity": Float,
    #     "linkquality": Int,     <- dismiss
    #     "temperature": Float,
    #     "voltage": Int}'      <- dismiss

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: str = None,
        v_temp: Optional[TemperatureSensor] = None,
        v_humi: Optional[HumiditySensor] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given device name, an optional friendly name,
        an optional topic base, and optional instances of `TemperatureSensor` and `HumiditySensor`.

        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name of the device. If not provided, it defaults to the device name.
        :type friendly_name: Optional[str]
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to BaseTopic.Z2M_BASE_TOPIC.
        :type base_topic: Optional[str]
        :param v_temp: An instance of `TemperatureSensor`. If not provided, a new instance is created.
        :type v_temp: Optional[TemperatureSensor]
        :param v_humi: An instance of `HumiditySensor`. If not provided, a new instance is created.
        :type v_humi: Optional[HumiditySensor]
        :raises TypeError: If v_temp is not an instance of `TemperatureSensor` or v_humi is not an instance of `HumiditySensor`.
        """
        friendly_name = friendly_name or device_name
        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        v_temp = v_temp or TemperatureSensor(friendly_name)
        if not isinstance(v_temp, TemperatureSensor):
            raise TypeError(
                f'"v_temp" must be an instance of TemperatureSensor, not {type(v_temp)}'
            )
        self._set_message_handler(
            self._root_topic, self.__class__._decode_temp_pl, v_temp
        )

        v_humi = v_humi or HumiditySensor(friendly_name)
        if not isinstance(v_humi, HumiditySensor):
            raise TypeError(
                f'"v_humi" must be an instance of HumiditySensor, not {type(v_humi)}'
            )
        self._set_message_handler(
            self._root_topic, self.__class__._decode_humi_pl, v_humi
        )

    def _decode_temp_pl(self, _topic, payload: dict) -> float:
        _value = payload.get("temperature")
        if _value is None:
            raise DecodingException(f'No "temperature" key in payload : {payload}')
        else:
            return float(_value)

    @abstractmethod
    def _decode_humi_pl(self, topic, payload) -> int:
        raise NotImplementedError


class SonoffSnzb02(SensorOnZigbee):
    """https://www.zigbee2mqtt.io/devices/SNZB-02.html#sonoff-snzb-02"""

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = payload.get("humidity")
        if _value is None:
            raise DecodingException(f'No "humidity" key in payload : {payload}')
        else:
            return int(_value)


class Ts0601Soil(SensorOnZigbee):
    """https://www.zigbee2mqtt.io/devices/TS0601_soil.html"""

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = payload.get("soil_moisture")
        if _value is None:
            raise DecodingException(f'No "soil_moisture" key in payload : {payload}')
        else:
            return int(_value)


class ButtonOnZigbee(DecoderOnZigbee2MQTT, metaclass=ABCMeta):
    """
    Represents a button device on the Zigbee2MQTT protocol.
    """

    #    <base_topic>
    #    └── <device_name> : <json_payload>      <== self._root_topic
    #
    # JSON payload example :
    #    {"action": "single" | "double" | "long"
    #     "battery": Int,       <- dismiss
    #     "linkquality": Int,   <- dismiss
    #     "voltage": Int}'      <- dismiss

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_button: Optional[Button] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given device name, an optional friendly name,
        an optional topic base, and an optional instance of `Button`.

        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name of the device. If not provided, it defaults to the device name.
        :type friendly_name: Optional[str]
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to None.
        :type base_topic: Optional[str]
        :param v_button: An instance of `Button`. If not provided, a new instance is created.
        :type v_button: Optional[Button]
        :raises TypeError: If v_button is not an instance of `Button`.
        """
        friendly_name = friendly_name or device_name
        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        v_button = v_button or Button(friendly_name)
        if not isinstance(v_button, Button):
            raise TypeError(
                f'"v_button" must be an instance of Button, not {type(v_button)}'
            )
        self._set_message_handler(
            self._root_topic, self.__class__._decode_value_pl, v_button
        )

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> str:
        raise NotImplementedError


class SonoffSnzb01(ButtonOnZigbee):
    """https://www.zigbee2mqtt.io/devices/SNZB-01.html#sonoff-snzb-01"""

    def _decode_value_pl(self, topic, payload) -> str:
        _pl = payload.get("action")
        action_map = {
            "single": BUTTON_SINGLE_ACTION,
            "double": BUTTON_DOUBLE_ACTION,
            "long": BUTTON_LONG_ACTION,
        }
        if _pl in action_map:
            return action_map[_pl]
        raise DecodingException(f'Received erroneous Action value : "{_pl}"')


class MotionOnZigbee(DecoderOnZigbee2MQTT, metaclass=ABCMeta):
    """Bridge between MOTION SENSOR devices and MQTT Clients"""

    #    <base_topic>
    #    └── <device_name> : <json_payload>      <== self._root_topic
    #
    # JSON payload example :
    #    {"occupancy": Bool,
    #     "tamper": Bool,       <- dismiss
    #     "battery": Int,       <- dismiss
    #     "battery_low": Bool,  <- dismiss
    #     "linkquality": Int,   <- dismiss
    #     "voltage": Int}'      <- dismiss

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_motion: Optional[Motion] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given device name, an optional friendly name,
        an optional topic base, and an optional instance of `Motion`.

        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name of the device. If not provided, it defaults to the device name.
        :type friendly_name: Optional[str]
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to None.
        :type base_topic: Optional[str]
        :param v_motion: An instance of `Motion`. If not provided, a new instance is created.
        :type v_motion: Optional[Motion]
        :raises TypeError: If v_motion is not an instance of `Motion`.
        """
        friendly_name = friendly_name or device_name
        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        v_motion = v_motion or Motion(friendly_name)
        if not isinstance(v_motion, Motion):
            raise TypeError(
                f'"v_motion" must be an instance of Motion, not {type(v_motion)}'
            )
        self._set_message_handler(
            self._root_topic, self.__class__._decode_value_pl, v_motion
        )

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> dict:
        raise NotImplementedError


class SonoffSnzb3(MotionOnZigbee):
    """https://www.zigbee2mqtt.io/devices/SNZB-03.html#sonoff-snzb-03"""

    def _decode_value_pl(self, topic, payload) -> bool:
        _value = payload.get("occupancy")
        if _value is None:
            raise DecodingException(f'No "occupancy" key in payload : {payload}')
        else:
            return _value


class AlarmOnZigbee(DecoderOnZigbee2MQTT, metaclass=ABCMeta):
    """
    Represents an alarm device on the Zigbee2MQTT protocol.
    """

    def __init__(
        self,
        encoder: IEncoder,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_alarm: Optional[Alarm] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given encoder, device name, an optional friendly name,
        an optional topic base, and an optional instance of `Alarm`.

        :param encoder: The encoder to be used for encoding.
        :type encoder: IEncoder
        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name of the device. If not provided, it defaults to the device name.
        :type friendly_name: Optional[str]
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to None.
        :type base_topic: Optional[str]
        :param v_alarm: An instance of `Alarm`. If not provided, a new instance is created.
        :type v_alarm: Optional[Alarm]
        :raises ValueError: If encoder is not an instance of `IEncoder` or v_alarm is not an instance of `Alarm`.
        """
        friendly_name = friendly_name or device_name
        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        v_alarm = v_alarm or Alarm(friendly_name)
        if not isinstance(encoder, IEncoder):
            raise ValueError(f"Bad value : {encoder} of type {type(encoder)}")
        if not isinstance(v_alarm, Alarm):
            raise ValueError(f"Bad value : {v_alarm} of type {type(v_alarm)}")
        v_alarm.encoder = encoder

        self._set_message_handler(
            self._root_topic, self.__class__._decode_value_pl, v_alarm
        )

    @abstractmethod
    def _decode_value_pl(self, topic, payload) -> bool:
        """Decode state payload."""
        raise NotImplementedError


class NeoNasAB02B2(AlarmOnZigbee):
    """https://www.zigbee2mqtt.io/devices/NAS-AB02B2.html"""

    _key_alarm = "alarm"

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_alarm: Optional[Alarm] = None,
    ) -> None:
        super().__init__(
            encoder=NeoNasAB02B2Encoder(get_root_topic(device_name, base_topic)),
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
            v_alarm=v_alarm,
        )

    def _decode_value_pl(self, topic, payload) -> bool:
        _pl = payload.get(self._key_alarm)
        if not isinstance(_pl, bool):
            raise DecodingException(f'Received erroneous payload : "{payload}"')
        return _pl


class NeoNasAB02B2Encoder(IEncoder):
    _key_alarm = "alarm"
    _key_melody = "melody"
    _key_alarm_level = "volume"
    _key_alarm_duration = "duration"

    def __init__(self, root_topic) -> None:
        self._root_topic = root_topic
        self._melody = 1
        self._alarm_level = "low"

    def set_sound(self, melody: int, alarm_level: str) -> None:
        """
        Sets the sound of the alarm.

        This method sets the melody and alarm level of the alarm. The melody must be an integer between 1 and 18,
        and the alarm level must be either 'low', 'medium', or 'high'.

        :param melody: The melody to be set. Must be an integer between 1 and 18.
        :type melody: int
        :param alarm_level: The alarm level to be set. Must be either 'low', 'medium', or 'high'.
        :type alarm_level: str
        :raises AssertionError: If melody is not an integer between 1 and 18, or if alarm_level is not 'low', 'medium', or 'high'.
        """
        assert isinstance(melody, int) and melody in range(
            1, 19
        ), f"Bad value for melody : {melody}"
        assert isinstance(alarm_level, str) and alarm_level in [
            "low",
            "medium",
            "high",
        ], f"Bad value for alarm_level : {alarm_level}"

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        return None

    def is_pulse_request_allowed(self, device_id: Optional[int] = None) -> bool:
        # Implement abstract method
        # Don't work with pulse
        return False

    def change_state_request(
        self,
        is_on: bool,
        device_id: Optional[int] = None,
        on_time: Optional[int] = None,
    ) -> tuple[str, str]:
        # Implement abstract method
        _set = {
            self._key_alarm: is_on,
            self._key_melody: self._melody,
            self._key_alarm_level: self._alarm_level,
            self._key_alarm_duration: on_time,
        }
        iotlib_logger.debug("Encode payload : %s", _set)
        return f"{self._root_topic}/set", json.dumps(_set)

    def device_configure_message(self) -> Optional[tuple[str, str]]:
        return None


class SwitchDecoder(DecoderOnZigbee2MQTT):
    """
    Represents a multi-switch device on the Zigbee2MQTT protocol.
    """

    def __init__(
        self,
        encoder: IEncoder,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: str = None,
        v_switch: Optional[Switch] = None,
        v_switch0: Optional[Switch0] = None,
        v_switch1: Optional[Switch1] = None,
    ) -> None:
        """
        Initializes a new instance of the class.

        This method initializes a new instance of the class with a given encoder, device name, an optional friendly name,
        an optional topic base, and optional instances of `Switch0` and `Switch1`.

        :param encoder: The encoder to be used for encoding.
        :type encoder: IEncoder
        :param device_name: The name of the device.
        :type device_name: str
        :param friendly_name: The friendly name of the device. If not provided, it defaults to the device name.
        :type friendly_name: Optional[str]
        :param base_topic: The base topic for MQTT communication. If not provided, it defaults to None.
        :type base_topic: Optional[str]
        :param v_switch: An instance of `Switch`. If not provided, a new instance is created.
        :type v_switch: Optional[Switch]
        :param v_switch0: An instance of `Switch0`. If not provided, a new instance is created.
        :type v_switch0: Optional[Switch0]
        :param v_switch1: An instance of `Switch1`. If not provided, a new instance is created.
        :type v_switch1: Optional[Switch1]
        :raises ValueError: If encoder is not an instance of `IEncoder`, v_switch0 is not an instance of `Switch0`, or v_switch1 is not an instance of `Switch1`.
        """
        friendly_name = friendly_name or device_name
        super().__init__(device_name=device_name,
                         friendly_name=friendly_name,
                         base_topic=base_topic)

        if not isinstance(encoder, IEncoder):
            raise TypeError(f"Bad type for {encoder} of type {type(encoder)}")
        if v_switch is not None:
            v_switch.encoder = encoder
            self._set_message_handler(
                self._root_topic, self.__class__._decode_switch_value_pl, v_switch
            )
        if v_switch0 is not None:
            v_switch0.encoder = encoder
            self._set_message_handler(
                self._root_topic, self.__class__._decode_switch0_value_pl, v_switch0
            )
        if v_switch1 is not None:
            v_switch1.encoder = encoder
            self._set_message_handler(
                self._root_topic, self.__class__._decode_switch1_value_pl, v_switch1
            )

    def _decode_generic_switch_value_pl(self, topic, payload, key_power) -> bool | None:
        """
        Decode the switch value from the payload.

        Args:
            topic (str): The topic of the message.
            payload (str): The payload of the message.
            key_power (str): The switch power identifier.

        Returns:
            bool | None: The decoded switch value. Returns True if the switch is on,
            False if the switch is off, and None if the switch identifier is invalid.

        Raises:
            DecodingException: If the state value or switch identifier is erroneous.
        """
        if not isinstance(payload, dict):
            raise DecodingException(
                f'Received erroneous payload : "{payload}" of type {type(payload)}'
            )

        _power_state = payload.get(key_power)
        if _power_state == PowerState.ON.value:
            return True
        elif _power_state == PowerState.OFF.value:
            return False
        elif _power_state is None:
            return None
        else:
            raise DecodingException(
                f'Received erroneous State value : "{_power_state}"'
            )

    def _decode_switch_value_pl(self, topic, payload) -> bool | None:
        return self._decode_generic_switch_value_pl(topic, payload, SWITCH_POWER)

    def _decode_switch0_value_pl(self, topic, payload) -> bool | None:
        return self._decode_generic_switch_value_pl(topic, payload, SWITCH0_POWER)

    def _decode_switch1_value_pl(self, topic, payload) -> bool | None:
        return self._decode_generic_switch_value_pl(topic, payload, SWITCH1_POWER)


class SwitchEncoder(IEncoder):
    def __init__(self, root_topic: str) -> None:
        self._root_topic = root_topic

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        # Implement abstract method
        _topic = f"{self._root_topic}/get"
        if device_id is None:
            _payload = '{"state":""}'
        else:
            _payload = '{"state_left":"","state_right":""}'
        return _topic, _payload

    def is_pulse_request_allowed(self, device_id: Optional[int] = None) -> bool:
        # Implement abstract method
        # Don't work with pulse
        return False

    def change_state_request(
        self,
        is_on: bool,
        device_id: Optional[int] = None,
        on_time: Optional[int] = None,
    ) -> tuple[str, str]:
        # Implement abstract method
        if device_id is None:
            _key_power = SWITCH_POWER
        elif device_id == 0:
            _key_power = SWITCH0_POWER
        elif device_id == 1:
            _key_power = SWITCH1_POWER
        else:
            raise ValueError(f"Bad value for device_id : {device_id}")

        _topic = f"{self._root_topic}/set"
        _json_pl = {_key_power: PowerState.ON.value if is_on else PowerState.OFF.value}
        if on_time is not None:
            _json_pl["on_time"] = on_time
        _payload = json.dumps(_json_pl)
        return _topic, _payload

    def device_configure_message(self) -> Optional[tuple[str, str]]:
        return None


class SonoffZbminiL(SwitchDecoder):
    """Bridge for Sonoff ZBMINI-L devices.
    https://www.zigbee2mqtt.io/devices/ZBMINI-L.html#sonoff-zbmini-l
    """

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_switch: Optional[Switch] = None,
    ) -> None:
        v_switch = v_switch or Switch(friendly_name)
        if not isinstance(v_switch, Switch):
            raise TypeError(f"Bad type for {v_switch} of type {type(v_switch)}")
        super().__init__(
            encoder=SwitchEncoder(get_root_topic(device_name, base_topic)),
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
            v_switch=v_switch,
        )


class TuYaTS0002(SwitchDecoder):
    """https://www.zigbee2mqtt.io/devices/TS0002.html"""

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: str = None,
        v_switch0: Optional[Switch0] = None,
        v_switch1: Optional[Switch1] = None,
    ) -> None:

        v_switch0 = v_switch0 or Switch(friendly_name)
        v_switch1 = v_switch1 or Switch(friendly_name)
        if not isinstance(v_switch0, Switch0):
            raise TypeError(f"Bad type for {v_switch0} of type {type(v_switch0)}")
        if not isinstance(v_switch1, Switch1):
            raise TypeError(f"Bad type for {v_switch1} of type {type(v_switch1)}")
        super().__init__(
            encoder=SwitchEncoder(get_root_topic(device_name, base_topic)),
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
            v_switch0=v_switch0,
            v_switch1=v_switch1,
        )
