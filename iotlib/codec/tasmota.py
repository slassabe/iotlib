#!/usr/local/bin/python3
# coding=utf-8
""" This module provides codec implementations for encoding/decoding data from 
Tasmota-based devices using MQTT.
"""

import enum
import json
from abc import ABCMeta, abstractmethod
from json.decoder import JSONDecodeError
from typing import Optional

from iotlib.abstracts import IEncoder
from iotlib.codec.core import Codec, DecodingException
from iotlib.utils import iotlib_logger
from iotlib.virtualdev import ADC, Switch, Switch0, Switch1, TemperatureSensor


class PowerState(enum.Enum):
    """Enumeration representing the power state of a Rasmota device.

    Attributes:

        ON (str): Constant representing the device being powered on.
            Has value ``'ON'``.

        OFF (str): Constant representing the device being powered off.
            Has value ``'OFF'``.
    """

    ON = "ON"
    OFF = "OFF"


class Availability(enum.Enum):
    """Enumeration representing the availability of a Tasmota device.

    The `Availability` enumeration defines three possible states for
    the availability of a Rasmota device:
    - `ONLINE`: The device is online and available.
    - `OFFLINE`: The device is offline and unavailable.
    - `NONE`: The availability status is unknown or not applicable.
    """

    ONLINE = "Online"
    OFFLINE = "Offline"
    NONE = None


_AVAILABILITY_VALUES = [avail.value for avail in Availability]


class DecoderOnTasmota(Codec):
    """Tasmota Codec implementation"""

    # sub-topic `tele` reports telemetry info on the device
    #    <base_topic>
    #    └── tele
    #        └── <device_name>
    #            ├── LWT : Online | Offline | None  <== self._availability_topic
    #            ├── POWER : ON | OFF
    #            └── SENSOR : <JSON payload >       <== self._tele_sensors_topic
    #
    # sub-topic `stat`` reports back status or configuration message
    #    <base_topic>
    #    └── stat
    #        └── <device_name>
    #            └── POWER : ON | OFF               <== self._stat_power_topic

    def __init__(
        self,
        encoder: Optional[IEncoder],
        device_name: str,
        friendly_name: Optional[str] = str,
        base_topic: Optional[str] = None,
    ) -> None:
        super().__init__(
            encoder=encoder,
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
        )

        _root_topic = f"{base_topic}/" if base_topic is not None else ""
        self._stat_power_topic = f"{_root_topic}stat/{device_name}/POWER"
        _tele_topic = f"{_root_topic}tele/{device_name}"
        self._tele_sensors_topic = f"{_tele_topic}/SENSOR"
        self._availability_topic = f"{_tele_topic}/LWT"

    def get_availability_topic(self) -> str:
        # Implement abstract method
        return self._availability_topic

    def decode_avail_pl(self, payload: str) -> bool:
        # Implement abstract method
        iotlib_logger.debug(
            ">> %s (%s) : decode availability payload", repr(payload), type(payload)
        )

        if payload not in _AVAILABILITY_VALUES:
            raise DecodingException(f"Payload value error: {payload}")
        return payload == Availability.ONLINE.value

    def _decode_state_pl(self, topic: str, payload: str) -> bool:
        if payload == PowerState.ON.value:
            return True
        elif payload == PowerState.OFF.value:
            return False
        elif payload == "":
            iotlib_logger.debug('"%s": is available', self)
        else:
            raise DecodingException(
                f'Received erroneous attribute value : "{payload}" on topic "{topic}"'
            )

    def _decode_json_pl(
        self, topic: str, payload: str, section_name: str, property_name: str
    ) -> any:
        """Decode a generic payload from a Tasmota device.

        Args:
            topic: The MQTT topic the payload was received on.
            payload: The payload string to decode.
            section_name: Name of the section in the JSON payload.
            property_name: Name of the property to extract.

        Returns:
            any: The decoded property value.

        Raises:
            DecodingException: If decoding fails.

        Decodes a payload by loading the JSON, extracting the section
        with name section_name, and getting the property property_name
        from that section. If any expected fields are missing, raises
        an DecodingException.
        """
        iotlib_logger.debug(
            '"%s": received %s value : "%s"', self, property_name, payload
        )
        try:
            _section_pl = json.loads(payload).get(section_name)
            if _section_pl is None:
                raise DecodingException(
                    f"Received erroneous attribute value :"
                    f'"{payload}" on "{topic}" - missing "{section_name}"'
                )
            _value = _section_pl.get(property_name)
            if _value is None:
                raise DecodingException(
                    f"Received erroneous attribute value :"
                    f'"{payload}" on "{topic}" - missing "{property_name}"'
                )
            return _value
        except JSONDecodeError as exp:
            raise DecodingException(
                f'Exception occured while decoding : "{payload}"'
            ) from exp


class EncoderOnTasmota(IEncoder, metaclass=ABCMeta):
    """Encoder for Tasmota devices."""

    # sub-topic `tele` reports telemetry info on the device
    #    <base_topic>
    #    └── tele
    #        └── <device_name>
    #            └── POWER : ON | OFF
    #
    # sub-topic `cmnd` prefix to issue commands or ask for status
    #    <base_topic>
    #    └── cmnd
    #        └── <device_name>                      <== self._base_cmd_topi
    #            ├── PulseTime (str)                <== self._cmnd_pulsetime_topic
    #            ├── Power : ON | OFF               <== self._cmnd_power_topic
    #            └── Backlog (str)                  <== self._cmnd_backlog_topic

    def __init__(self, device_name: str, base_topic: Optional[str] = None) -> None:

        _root_topic = f"{base_topic}/" if base_topic is not None else ""
        self._base_cmd_topic = f"{_root_topic}cmnd/{device_name}"
        self._cmnd_pulsetime_topic = f"{self._base_cmd_topic}/PulseTime"
        self._cmnd_power_topic = f"{self._base_cmd_topic}/Power"
        self._cmnd_backlog_topic = f"{self._base_cmd_topic}/Backlog"
        super().__init__()

    def get_state_request(self, device_id: Optional[int] = None) -> tuple[str, str]:
        # Implement abstract method
        # cmnd/tasmota_switch/Power : an empty message/payload sends a status query
        _topic = self._cmnd_power_topic
        if device_id is not None:
            _topic += f"{device_id}"
        _pl = ""
        return _topic, _pl

    def change_state_request(
        self,
        is_on: bool,
        device_id: Optional[int] = None,
        on_time: Optional[str] = None,
    ) -> tuple[str, str]:
        # Implement abstract method
        def _encode_state_pl(is_on: bool) -> None:
            return PowerState.ON.value if is_on else PowerState.OFF.value

        _topic = self._cmnd_power_topic
        if device_id is not None:
            _topic += f"{device_id}"
        _pl = _encode_state_pl(is_on)
        iotlib_logger.info('[%s] sending  "%s" on topic "%s"', self, _pl, _topic)
        return _topic, _pl

    def is_pulse_request_allowed(self, device_id: Optional[int] = None) -> bool:
        # Implement abstract method
        return False

    def format_backlog_cmnd(self, cmnd) -> tuple[str, str]:
        """Configure the device.

        [Reference] (<https://tasmota.github.io/docs/Commands/#the-power-of-backlog>)
        """
        _topic = self._cmnd_backlog_topic
        return _topic, cmnd

    def change_state_request_PULSE(
        self,
        is_on: bool,
        device_id: Optional[int] = None,
        on_time: Optional[str] = None,
    ) -> tuple[str, str]:
        # Implement abstract method
        if on_time is not None:
            if not isinstance(on_time, int):
                raise TypeError(f"Value {on_time} is not of type int")
            if on_time < 0:
                raise ValueError(f"Bad value for duration: {on_time}, must be >= 0")

        if is_on:
            _topic = self._cmnd_pulsetime_topic
            # set PulseTime for Relay<x>, offset by 100, in 1 second increments.
            # Add 100 to desired interval in seconds,
            # e.g., PulseTime 113 = 13 seconds
            #       PulseTime 460 = 6 minutes (i.e., 360 seconds)
            _payload = 0 if on_time is None else 100 + on_time
        else:
            _topic = self._cmnd_power_topic
            _payload = self._encode_state_pl(is_on)

        if device_id is not None:
            _topic += f"{device_id}"

        iotlib_logger.info(
            '"%s": sending payload: "%s" on topic: "%s"', self, _payload, _topic
        )
        return _topic, _payload

    @abstractmethod
    def get_device_config_message(self) -> tuple[str, str]:
        """Configure the device."""


class TasmotaPlugS(DecoderOnTasmota):
    """Represents a Shelly Plug S device and  provides methods for controlling and
    retrieving its state over Tasmota MQTT.
    """

    # JSON payload example :
    # {"Time":"2024-04-16T09:15:03",
    #  "ANALOG":{"Temperature":28.6},
    #  "ENERGY":{"TotalStartTime":"2023-11-13T19:36:00",
    #            "Total":235.645,
    #            "Yesterday":0.000,
    #            "Today":0.015,
    #            "Period":2,
    #            "Power":24,
    #            "ApparentPower":24,
    #            "ReactivePower":0,
    #            "Factor":1,
    #            "Voltage":237,
    #            "Current":0.099},
    #  "TempUnit":"C"}

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_switch0: Optional[Switch] = None,
        v_temp: Optional[TemperatureSensor] = None,
        v_adc: Optional[ADC] = None,
    ) -> None:
        friendly_name = friendly_name or device_name
        _encoder = TasmotaPlugSEncoder(
            device_name=device_name,
            base_topic=base_topic,
        )
        super().__init__(
            encoder=_encoder,
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
        )
        v_switch0 = v_switch0 or Switch(friendly_name)
        v_temp = v_temp or TemperatureSensor(friendly_name)
        v_adc = v_adc or ADC(friendly_name)
        if not isinstance(v_switch0, Switch):
            raise TypeError(
                f'"v_switch0" must be an instance of Switch, not {type(v_switch0)}'
            )
        if not isinstance(v_temp, TemperatureSensor):
            raise TypeError(
                f'"v_temp" must be an instance of TemperatureSensor, not {type(v_temp)}'
            )
        if not isinstance(v_adc, ADC):
            raise TypeError(f'"v_temp" must be an instance of ADC, not {type(v_adc)}')

        v_switch0.encoder = _encoder
        self._set_message_handler(
            self._stat_power_topic, self.__class__._decode_state_pl, v_switch0
        )
        self._set_message_handler(
            self._tele_sensors_topic, self.__class__._decode_temp_pl, v_temp
        )
        self._set_message_handler(
            self._tele_sensors_topic, self.__class__._decode_voltage_pl, v_adc
        )

    def _decode_voltage_pl(self, topic: str, payload: str) -> float:
        """Decode voltage payload from Tasmota device.

        Args:
            topic (str): The MQTT topic of the message.
            payload (str): The payload string.

        Returns:
            float: The decoded voltage value.

        """
        _value = self._decode_json_pl(topic, payload, "ENERGY", "Voltage")
        return float(_value)

    def _decode_temp_pl(self, topic: str, payload: str) -> float:
        """Decode temperature value from Tasmota MQTT payload.

        Args:
            topic: The MQTT topic for the message.
            payload: The payload containing the temperature.

        Returns:
            float: The decoded temperature value.

        """
        _value = self._decode_json_pl(topic, payload, "ANALOG", "Temperature")
        return float(_value)


class TasmotaPlugSEncoder(EncoderOnTasmota):

    def get_device_config_message(self) -> tuple[str, str]:
        # Implement IEncoder interface method
        return self.format_backlog_cmnd("PulseTime 0")  # Reset pulseTime


class TasmotaUni(DecoderOnTasmota):
    """TasmotaUni class.

    This class represents Shelly UNI device over Tasmota.
    Manage MQTT topics and publish to them.

    Attributes:
        device_name (str): The name of the Shelly UNI device.
        v_swit0 (VirtualSwitch): The virtual switch for switch 0.
        v_swit1 (VirtualSwitch): The virtual switch for switch 1.
        v_adc (VirtualADC): The virtual ADC sensor.

    """

    # JSON payload example :
    #
    # {"Time":"2024-04-16T09:48:02",
    #   "Switch1":"ON",
    #   "Switch2":"ON",
    #   "Switch3":"OFF",
    #   "ANALOG":{"Range":1141},
    #   "AM2301":{"Temperature":null,"Humidity":null,"DewPoint":null},
    # "TempUnit":"C"}

    def __init__(
        self,
        device_name: str,
        friendly_name: Optional[str] = None,
        base_topic: Optional[str] = None,
        v_switch0: Optional[Switch0] = None,
        v_switch1: Optional[Switch1] = None,
        v_adc: Optional[ADC] = None,
    ) -> None:
        friendly_name = friendly_name or device_name
        _encoder = TasmotaUniEncoder(
            device_name=device_name,
            base_topic=base_topic,
        )
        super().__init__(
            encoder=_encoder,
            device_name=device_name,
            friendly_name=friendly_name,
            base_topic=base_topic,
        )
        v_switch0 = v_switch0 or Switch(friendly_name)
        v_switch1 = v_switch1 or Switch(friendly_name)
        v_adc = v_adc or ADC(friendly_name)
        if not isinstance(v_switch0, Switch0):
            raise TypeError(
                f'"v_switch0" must be an instance of Switch0, not {type(v_switch0)}'
            )
        if not isinstance(v_switch1, Switch1):
            raise TypeError(
                f'"v_switch1" must be an instance of Switch1, not {type(v_switch1)}'
            )
        if not isinstance(v_adc, ADC):
            raise TypeError(f'"v_temp" must be an instance of ADC, not {type(v_adc)}')

        for _v_switch in [v_switch0, v_switch1]:
            _v_switch.encoder = _encoder
            self._set_message_handler(
                f"{self._stat_power_topic}{_v_switch.device_id}",
                self.__class__._decode_state_pl,
                _v_switch,
            )

        self._set_message_handler(
            self._tele_sensors_topic, self.__class__._decode_voltage_pl, v_adc
        )

    def _decode_voltage_pl(self, topic: str, payload: str) -> float:
        """Decode voltage payload from Tasmota device.

        Args:
            topic (str): The MQTT topic of the message.
            payload (str): The payload string.

        Returns:
            float: The decoded voltage value.

        """
        _value = self._decode_json_pl(topic, payload, "ANALOG", "Range")
        _value = float(_value / 100)
        iotlib_logger.debug('"%s": _decode_voltage_pl: %s', self, _value)
        return _value


class TasmotaUniEncoder(EncoderOnTasmota):

    def get_device_config_message(self) -> tuple[str, str]:
        # Implement IEncoder interface method
        # Reset pulseTime and set AdcParam
        return self.format_backlog_cmnd("PulseTime 0; AdcParam 6,0,71,0,100")
