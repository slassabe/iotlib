#!/usr/local/bin/python3
# coding=utf-8

"""Module containing factory methods to create device cluster instances.

This module provides a factory for creating instances of devices and their
associated clusters. The factory registers device models, protocols, and 
the corresponding cluster classes. 

The primary class is ClusterFactory. It maintains a registry mapping models
and protocols to the cluster classes. The create_instance() method is used
to lookup and instantiate the appropriate cluster for a given model and 
protocol.

Custom device types can be registered using the registers() method before
calling create_instance().

Example usage:

    factory = ClusterFactory()
    factory.registers(Model.CUSTOM_DEVICE, Protocol.ZIGBEE, CustomCluster) 
    
    cluster = factory.create_instance(Model.CUSTOM_DEVICE, Protocol.ZIGBEE)
"""
from iotlib import package_level_logger

from collections import defaultdict
from enum import Enum
from typing import Callable

from iotlib.abstracts import AbstractCodec
from iotlib.codec.z2m import (NeoNasAB02B2, SonoffSnzb01, SonoffSnzb02, SonoffSnzb3,
                              SonoffZbminiL, Ts0601Soil, EweLinkZbSw02)

from .utils import Singleton


class Model(Enum):
    """
    This enum class Model defines constants for the different device models supported.

    - MIFLORA: Xiaomi Mi Flora plant sensor  
    - NEO_ALARM: Neo NAS-AB02B2 Zigbee Siren
    - SHELLY_PLUGS: Shelly Plug S WiFi smart plug
    - SHELLY_UNI: Shelly Uni WiFi relay/dimmer
    - TUYA_SOIL: Tuya TS0601_soil Zigbee soil moisture sensor
    - ZB_AIRSENSOR: Sonoff Zigbee air temperature/humidity sensor
    - ZB_BUTTON: Sonoff SNZB-01 Zigbee wireless button
    - ZB_MOTION: Sonoff SNZB-03 Zigbee motion sensor  
    - ZB_MINI: Sonoff ZBMINI-L Zigbee wireless switch module
    - EL_ZBSW02: eWeLink ZB-SW02 Zigbee wireless switch module

    """
    EL_ZBSW02 = 'ZB-SW02' # eWeLink ZB-SW02 Zigbee wireless switch module
    MIFLORA = 'Miflora'
    NEO_ALARM = 'NAS-AB02B2'  # Neo NAS-AB02B2 Zigbee Siren
    RING_CAMERA = 'RingCamera'
    SHELLY_PLUGS = 'Shelly Plug S'  # Shelly Plug S WiFi smart plug
    SHELLY_UNI = 'Shelly Uni'  # Shelly Uni WiFi relay/dimmer
    TUYA_SOIL = 'TS0601_soil'  # TuYa TS0601_soil Zigbee soil moisture sensor
    ZB_AIRSENSOR = "SNZB-02"  # SONOFF Zigbee air temperature/humidity sensor
    ZB_BUTTON = "SNZB-01"   # SONOFF SNZB-01 Zigbee wireless button
    ZB_MOTION = 'SNZB-03'   # SONOFF SNZB-03 Zigbee motion sensor
    ZB_MINI = 'ZBMINI-L'    # SONOFF ZBMINI-L Zigbee wireless switch module
    NONE = 'None'          # No model
    UNKNOWN = 'Unknown'    # Unknown model

    @staticmethod
    def from_str(label: str):
        """Return the Model enum value corresponding to the given label."""
        if label is None:
            return Model.NONE
        for model in Model:
            if model.value == label:
                return model
        return Model.UNKNOWN


class Protocol(Enum):
    """ An enumeration defining constants for different device communication protocols.

    - HOMIE: The Homie IoT protocol.
    - SHELLY: The Shelly smart home devices protocol.
    - TASMOTA: The Tasmota protocol used by ESP8266/ESP32 boards.
    - Z2M: The Zigbee2MQTT protocol.
    - Z2T: The Zigbee2Tasmota protocol.

    """
    DEFAULT = 'default'
    HOMIE = 'Homie'
    RING = 'Ring'
    SHELLY = 'Shelly'
    TASMOTA = 'Tasmota'
    Z2M = 'Zigbee2MQTT'
    Z2T = 'Zigbee2Tasmota'


class CodecFactory(metaclass=Singleton):
    """Factory class to create device instances.

    This class implements the Factory design pattern to instantiate 
    devices and components. It registers constructors and creates 
    instances on demand.

    Attributes:
        _constructors (dict): Registered constructors mapped to model name.

    """
    def __init__(self):
        """Initialize the factory by creating an empty constructors dict."""
        self._constructors = defaultdict(dict)

    def registers(self,
                  model: Model,
                  protocol: Protocol,
                  constructor: Callable[[list], AbstractCodec]) -> None:
        """Register a constructor for the given model.

        Args:
            model (Model): The model object representing the device model.
            protocol (Protocol): The protocol object for the communication protocol.
            constructor (Callable): The constructor function to register.

        Raises:
            TypeError: If model is not a Model object.
            TypeError: If protocol is not a Protocol object. 
            TypeError: If constructor is not callable.

        """
        package_level_logger.debug('Registering constructor for model %s and protocol %s',
                           model, protocol)
        if not isinstance(model, Model):
            raise TypeError(f'Model {model} is not of type "Model"')
        if not isinstance(protocol, Protocol):
            raise TypeError(f'Protocole {protocol} is not of type "Protocole"')
        if not isinstance(constructor, Callable):
            raise TypeError(
                f'Constructor {constructor} is not of type "Callable"')
        self._constructors[model][protocol] = constructor

    def _get_constructor(self, model: str, protocol=None) -> Callable[[list], AbstractCodec]:
        """Get the constructor callable for the given model and protocol.

        Args:
            model (str): The device model name
            protocol (Protocol, optional): The protocol enum value. Defaults to Protocol.DEFAULT.

        Returns:
            Callable: The constructor if found, raises ValueError otherwise.

        Raises:
            ValueError: If model is unknown or a constructor cannot be found 

        """
        _constructor_dict = self._constructors.get(model)
        if not _constructor_dict:
            raise ValueError(f'Cannot create instance for model: {model}')
        if _constructor_dict is None:
            raise ValueError(f'Cannot create instance for model: {model}')
        if len(_constructor_dict) == 1 and protocol is Protocol.DEFAULT:
            protocol = list(_constructor_dict.keys())[0]

        _constructor = _constructor_dict.get(protocol)
        if not _constructor:
            raise ValueError(
                f'Unable to create instance for model {model} and protocol {protocol}')
        return _constructor

    def create_instance(self,
                        model: Model,
                        protocol: Protocol,
                        *args,
                        **kwargs) -> AbstractCodec:
        """Create an instance of a Codec for the given model and protocol.

        Args:
            model (Model): The model enum for the device type.
            protocol (Protocol): The protocol enum for the communication protocol.
            *args: Positional arguments to pass to the constructor.
            **kwargs: Keyword arguments to pass to the constructor.

        Returns:
            AbstractCodec: An instance of an AbstractCodec subclass corresponding to 
            the given  model and protocol.

        Raises:
            TypeError: If model or protocol are not of the correct enum type.

        This looks up the appropriate AbstractCodec subclass based on the model and 
        protocol, instantiates it using the provided arguments, and returns the 
        instance.
        """
        if not isinstance(model, Model):
            raise TypeError(f"Model {model} is not of type Model")
        if not isinstance(protocol, Protocol):
            raise TypeError(f"Protocole {protocol} is not of type Protocol")

        _constructor = self._get_constructor(model, protocol)
        _codec = _constructor(*args, **kwargs)
        return _codec


CodecFactory().registers(Model.EL_ZBSW02, Protocol.Z2M, EweLinkZbSw02)
CodecFactory().registers(Model.NEO_ALARM, Protocol.Z2M, NeoNasAB02B2)
CodecFactory().registers(Model.TUYA_SOIL, Protocol.Z2M, Ts0601Soil)
CodecFactory().registers(Model.ZB_AIRSENSOR, Protocol.Z2M, SonoffSnzb02)
CodecFactory().registers(Model.ZB_BUTTON, Protocol.Z2M, SonoffSnzb01)
CodecFactory().registers(Model.ZB_MOTION, Protocol.Z2M, SonoffSnzb3)
CodecFactory().registers(Model.ZB_MINI, Protocol.Z2M, SonoffZbminiL)
