#!/usr/local/bin/python3
# coding=utf-8

"""
Module containing factory methods and enums for device models and protocols.

This module provides a factory for creating instances of codecs for different device 
models and protocols. It also defines enums for representing different device models and c
ommunication protocols.

The primary classes are Model and Protocol enums, and the CodecFactory. The Model enum 
represents different device models, and the Protocol enum represents different communication 
protocols. The CodecFactory uses these enums to create appropriate codec instances.

:Example: 

.. code-block:: python

    # factory.py code
    factory = CodecFactory()
    factory.registers(Model.NEO_ALARM, Protocol.ZIGBEE, NeoNasAB02B2) 

    # User code to discover device model and protocol
    import iotlib.factory as factory
    codec = factory.create_instance(Model.NEO_ALARM, Protocol.ZIGBEE)

The example above shows how to use the CodecFactory to register a codec for a specific 
device model and protocol, and create an instance of it.
"""

from collections import defaultdict
from enum import Enum
from typing import Callable

from iotlib.abstracts import ICodec
from iotlib.codec.z2m import (NeoNasAB02B2, SonoffSnzb01, SonoffSnzb02,
                              SonoffSnzb3, SonoffZbminiL, Ts0601Soil,
                              TuYaTS0002)
from iotlib.utils import Singleton, iotlib_logger


class Model(str, Enum):
    """
    This enum is used to represent the different models of devices that can be discovered.

    :ivar  MIFLORA: Xiaomi Mi Flora plant sensor
    :ivar  NEO_ALARM: Neo NAS-AB02B2 Zigbee Siren
    :ivar  SHELLY_PLUGS: Shelly Plug S WiFi smart plug
    :ivar  SHELLY_UNI: Shelly Uni WiFi relay/dimmer
    :ivar  TUYA_SOIL: Tuya TS0601_soil Zigbee soil moisture sensor
    :ivar  ZB_AIRSENSOR: Sonoff Zigbee air temperature/humidity sensor
    :ivar  ZB_BUTTON: Sonoff SNZB-01 Zigbee wireless button
    :ivar  ZB_MOTION: Sonoff SNZB-03 Zigbee motion sensor
    :ivar  ZB_MINI: Sonoff ZBMINI-L Zigbee wireless switch module
    :ivar  EL_ZBSW02: eWeLink ZB-SW02 Zigbee wireless switch module

    """

    TUYA_TS0002 = "TS0002"  # TuYa TS0002 Zigbee wireless switch module
    MIFLORA = "Miflora"
    NEO_ALARM = "NAS-AB02B2"  # Neo NAS-AB02B2 Zigbee Siren
    RING_CAMERA = "RingCamera"
    SHELLY_PLUGS = "Shelly Plug S"  # Shelly Plug S WiFi smart plug
    SHELLY_UNI = "Shelly Uni"  # Shelly Uni WiFi relay/dimmer
    TUYA_SOIL = "TS0601_soil"  # TuYa TS0601_soil Zigbee soil moisture sensor
    ZB_AIRSENSOR = "SNZB-02"  # SONOFF Zigbee air temperature/humidity sensor
    ZB_BUTTON = "SNZB-01"  # SONOFF SNZB-01 Zigbee wireless button
    ZB_MOTION = "SNZB-03"  # SONOFF SNZB-03 Zigbee motion sensor
    ZB_MINI = "ZBMINI-L"  # SONOFF ZBMINI-L Zigbee wireless switch module
    NONE = "None"  # No model
    UNKNOWN = "Unknown"  # Unknown model

    @staticmethod
    def from_str(label: str):
        """
        Returns the Model enum value corresponding to the given label.

        This method takes a label as input and returns the corresponding Model enum value.
        If the label does not correspond to any Model enum value, it returns None.

        :param label: The label to get the Model enum value for.
        :type label: str
        :return: The Model enum value corresponding to the label, or None if the label does not
            correspond to any Model enum value.
        :rtype: Model
        """
        if label is None:
            return Model.NONE
        for model in Model:
            if model.value == label:
                return model
        return Model.UNKNOWN


class Protocol(Enum):
    """
    This enum is used to represent the different communication protocols that can be used
    by devices.

    :ivar HOMIE: The Homie IoT protocol.
    :ivar SHELLY: The Shelly smart home devices protocol.
    :ivar TASMOTA: The Tasmota protocol used by ESP8266/ESP32 boards.
    :ivar Z2M: The Zigbee2MQTT protocol.
    :ivar Z2T: The Zigbee2Tasmota protocol.
    """

    DEFAULT = "default"
    HOMIE = "Homie"
    RING = "Ring"
    SHELLY = "Shelly"
    TASMOTA = "Tasmota"
    Z2M = "Zigbee2MQTT"
    Z2T = "Zigbee2Tasmota"


class CodecFactory(metaclass=Singleton):
    """
    A factory class for creating codec instances.

    This class uses the Singleton design pattern to ensure that only one instance of the factory
    exists. The factory can be used to create instances of different types of codecs.

    :ivar codecs: A dictionary mapping codec names to codec instances.
    :vartype codecs: dict[str, Codec]
    """

    def __init__(self):
        """Initialize the factory by creating an empty constructors dict."""
        self._constructors = defaultdict(dict)

    def registers(
        self, model: Model, protocol: Protocol, constructor: Callable[[list], ICodec]
    ) -> None:
        """
        Registers a new codec constructor.

        This method takes a model, a protocol, and a constructor function, and registers
        the constructor for creating codecs for the given model and protocol.

        :param model: The model for which the constructor should be registered.
        :type model: Model
        :param protocol: The protocol for which the constructor should be registered.
        :type protocol: Protocol
        :param constructor: The constructor function to be registered.
        :type constructor: Callable[[list], ICodec]
        """
        iotlib_logger.debug(
            "Registering constructor for model %s and protocol %s", model, protocol
        )
        if not isinstance(model, Model):
            raise TypeError(f'Model {model} is not of type "Model"')
        if not isinstance(protocol, Protocol):
            raise TypeError(f'Protocole {protocol} is not of type "Protocole"')
        if not isinstance(constructor, Callable):
            raise TypeError(f'Constructor {constructor} is not of type "Callable"')
        self._constructors[model][protocol] = constructor

    def _get_constructor(self, model: str, protocol=None) -> Callable[[list], ICodec]:
        """
        Retrieves the constructor for a given model and protocol.

        This method takes a model and an optional protocol, and returns the constructor function
        for creating codecs for the given model and protocol. If no protocol is provided, it
        returns the constructor for the given model regardless of the protocol.

        :param model: The model for which the constructor should be retrieved.
        :type model: str
        :param protocol: The protocol for which the constructor should be retrieved,
            defaults to None.
        :type protocol: Protocol, optional
        :return: The constructor function for the given model and protocol.
        :rtype: Callable[[list], ICodec]
        """
        _constructor_dict = self._constructors.get(model)
        if not _constructor_dict:
            raise ValueError(f"Cannot create instance for model: {model}")
        if _constructor_dict is None:
            raise ValueError(f"Cannot create instance for model: {model}")
        if len(_constructor_dict) == 1 and protocol is Protocol.DEFAULT:
            protocol = list(_constructor_dict.keys())[0]

        _constructor = _constructor_dict.get(protocol)
        if not _constructor:
            raise ValueError(
                f"Unable to create instance for model {model} and protocol {protocol}"
            )
        return _constructor

    def create_instance(
        self, model: Model, protocol: Protocol, *args, **kwargs
    ) -> ICodec:
        """
        Creates a new codec instance for the given model and protocol.

        This method takes a model, a protocol, and optional arguments, and creates a new
        codec instance for the given model and protocol using the registered constructor.

        :param model: The model for which the codec should be created.
        :type model: Model
        :param protocol: The protocol for which the codec should be created.
        :type protocol: Protocol
        :param args: Additional positional arguments to be passed to the constructor.
        :param kwargs: Additional keyword arguments to be passed to the constructor.
        :return: A new codec instance for the given model and protocol.
        :rtype: ICodec
        """
        if not isinstance(model, Model):
            raise TypeError(f"Model {model} is not of type Model")
        if not isinstance(protocol, Protocol):
            raise TypeError(f"Protocole {protocol} is not of type Protocol")

        _constructor = self._get_constructor(model, protocol)
        _codec = _constructor(*args, **kwargs)
        return _codec


CodecFactory().registers(Model.TUYA_TS0002, Protocol.Z2M, TuYaTS0002)
CodecFactory().registers(Model.NEO_ALARM, Protocol.Z2M, NeoNasAB02B2)
CodecFactory().registers(Model.TUYA_SOIL, Protocol.Z2M, Ts0601Soil)
CodecFactory().registers(Model.ZB_AIRSENSOR, Protocol.Z2M, SonoffSnzb02)
CodecFactory().registers(Model.ZB_BUTTON, Protocol.Z2M, SonoffSnzb01)
CodecFactory().registers(Model.ZB_MOTION, Protocol.Z2M, SonoffSnzb3)
CodecFactory().registers(Model.ZB_MINI, Protocol.Z2M, SonoffZbminiL)
