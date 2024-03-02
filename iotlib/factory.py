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

from enum import Enum
from typing import Callable, List
import logging

from abc import ABC, abstractmethod
from collections import defaultdict

from iotlib.client import MQTTClientBase
from iotlib.bridge import Surrogate
from iotlib.codec.z2m import (NeoNasAB02B2, SonoffSnzb01, SonoffSnzb02, SonoffSnzb3,
                                    SonoffZbminiL, Ts0601Soil, SonoffZbSw02Right)
from iotlib.processor import PropertyPublisher, VirtualDeviceLogger, ButtonTrigger, AvailabilityLogger, AvailabilityPublisher

from iotlib.virtualdev import (VirtualDevice, Alarm, ADC, Button,
                                HumiditySensor, Motion, Switch,
                                TemperatureSensor, LightSensor, ConductivitySensor)

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
    - ZB_SW02: eWeLink ZB-SW02 Zigbee wireless switch module

    """
    MIFLORA = 'Miflora'
    NEO_ALARM = 'NeoAlarm'
    RING_CAMERA = 'RingCamera'
    SHELLY_PLUGS = 'ShellyPlugS'
    SHELLY_UNI = 'ShellyUni'
    TUYA_SOIL = 'TuyaSoilSensor'
    ZB_AIRSENSOR = "ZBairsensor"
    ZB_BUTTON = "ZBbutton"
    ZB_MOTION = 'ZBmotion'
    ZB_MINI = 'ZBmini'
    ZB_SW02 = 'ZBsw02'


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


class Cluster(ABC):
    """Abstract base class representing a cluster of devices.

    This class defines the common interface and attributes for a cluster 
    of devices that will be managed together. 

    Attributes:
        model (Model): The model instance associated with this cluster.
        device_name (str): The unique name identifier for this device cluster.
        friendly_name (str): A human readable name for this cluster.
        bridge (MQTTBridge): The bridge instance associated with the cluster.
            This gets set during device enrollment.

    """

    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 ):
        self.model = model
        self.protocol = protocol,
        self.device_name = device_name
        self.friendly_name = friendly_name or device_name
        self.bridge = None

    def declare_virtual_devices(self, virtual_devices: List[VirtualDevice]):
        for virt_dev in virtual_devices:
            assert isinstance(
                virt_dev, VirtualDevice), f"Item {virt_dev} is not a VirtualDevice instance"
            virt_dev.processor_append(VirtualDeviceLogger())

    @abstractmethod
    def enroll_device(self) -> Surrogate:
        """Enroll the device with a bridge.

        This method should handle connecting to the appropriate bridge, 
        registering the device, and storing the bridge instance.

        Returns:
            MQTTBridge: The bridge instance associated with this device cluster.

        Raises:
            NotImplementedError: This method must be implemented in subclasses.

        """
        raise NotImplementedError


class ClusterFactory(metaclass=Singleton):
    """Factory class to create device instances.

    This class implements the Factory design pattern to instantiate 
    devices and components. It registers constructors and creates 
    instances on demand.

    Attributes:
        _constructors (dict): Registered constructors mapped to model name.

    """
    _logger = logging.getLogger(__name__)

    def __init__(self):
        """Initialize the factory by creating an empty constructors dict."""
        self._constructors = defaultdict(dict)

    def registers(self, model: Model, protocol: Protocol, constructor: Callable) -> None:
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
        self._logger.debug('Registering constructor for model %s and protocol %s',
                           model, protocol)
        if not isinstance(model, Model):
            raise TypeError(f'Model {model} is not of type "Model"')
        if not isinstance(protocol, Protocol):
            raise TypeError(f'Protocole {protocol} is not of type "Protocole"')
        if not isinstance(constructor, Callable):
            raise TypeError(
                f'Constructor {constructor} is not of type "Callable"')
        self._constructors[model][protocol] = constructor

    def _get_constructor(self, model: str, protocol=None) -> Callable:
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
            raise ValueError(f'Model {model} unknown')
        if _constructor_dict is None:
            raise ValueError(f'Model {model} unknown')
        if len(_constructor_dict) == 1 and protocol is Protocol.DEFAULT:
            protocol = list(_constructor_dict.keys())[0]

        _constructor = _constructor_dict.get(protocol)
        if not _constructor:
            raise ValueError(
                f'Unable to create instance for model {model} and protocol {protocol}')
        return _constructor

    def create_instance(self, model: Model, protocol: Protocol, device_name: str, *args, **kwargs) -> Cluster:
        """Create an instance of a Cluster for the given model and protocol.

        Args:
            model (Model): The model enum for the device type.
            protocol (Protocol): The protocol enum for the communication protocol.
            devive_name (str): The unique device name.
            *args: Positional arguments to pass to the constructor.
            **kwargs: Keyword arguments to pass to the constructor.

        Returns:
            Cluster: An instance of a Cluster subclass corresponding to the given
            model and protocol.

        Raises:
            TypeError: If model or protocol are not of the correct enum type.

        This looks up the appropriate Cluster subclass based on the model and 
        protocol, instantiates it using the provided arguments, and returns the 
        instance.
        """
        def _set_processors(bridge: Surrogate, 
                            device_name: str):
            # This will log availability changes
            bridge.avail_proc_append(AvailabilityLogger(device_name))
            # This will publish availability changes on MQTT
            bridge.avail_proc_append(AvailabilityPublisher(device_name, bridge.client))
            # This will publish property changes on MQTT
            bridge.property_proc_append(PropertyPublisher(bridge.client))
            # Silent mode:
            # self.property_proc_append(PropertyLogger())

        if not isinstance(model, Model):
            raise TypeError(
                f"Model {model} is not of type Model or is not defined")
        if not isinstance(protocol, Protocol):
            raise TypeError(
                f"Protocole {protocol} is not of type Protocole or is not defined")

        _constructor = self._get_constructor(model, protocol)
        _cluster = _constructor(model, protocol, device_name, *args, **kwargs)
        _bridge = _cluster.enroll_device()
        _cluster.bridge = _bridge
        
        _set_processors(_bridge, device_name)

        return _cluster


# Device customization

class _ClusterAirSensoir(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 quiet_mode=False,
                 v_temp=None,
                 v_humi=None,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_temp = v_temp or TemperatureSensor(self.friendly_name)
        self.virt_humi = v_humi or HumiditySensor(self.friendly_name)

        self.virt_temp._quiet_mode = quiet_mode
        self.virt_humi._quiet_mode = quiet_mode

        self.declare_virtual_devices([self.virt_temp, self.virt_humi])


class _ClusterSonoffSnzb02(_ClusterAirSensoir):
    def enroll_device(self) -> MQTTBridge:
        return SonoffSnzb02(self.device_name,
                            v_temp=self.virt_temp,
                            v_humi=self.virt_humi,
                            )


ClusterFactory().registers(Model.ZB_AIRSENSOR, Protocol.Z2M,
                           _ClusterSonoffSnzb02)


class _ClusterTs0601Soil(_ClusterAirSensoir):
    def enroll_device(self) -> MQTTBridge:
        return Ts0601Soil(self.device_name,
                          v_temp=self.virt_temp,
                          v_humi=self.virt_humi,
                          )


ClusterFactory().registers(Model.TUYA_SOIL, Protocol.Z2M,
                           _ClusterTs0601Soil)


class _ClusterMiflora(_ClusterAirSensoir):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 quiet_mode=False,
                 v_temp=None,
                 v_humi=None,
                 v_light=None,
                 v_cond=None,
                 ):
        super().__init__(model,
                         protocol,
                         device_name,
                         friendly_name,
                         quiet_mode,
                         v_temp,
                         v_humi,
                         )
        self.virt_light = v_light or LightSensor(self.friendly_name)
        self.virt_cond = v_cond or ConductivitySensor(self.friendly_name)

        self.virt_light._quiet_mode = quiet_mode
        self.virt_cond._quiet_mode = quiet_mode

        self.declare_virtual_devices([self.virt_light, self.virt_cond])

    def enroll_device(self) -> MQTTBridge:
        return Miflora(self.device_name,
                       v_temp=self.virt_temp,
                       v_humi=self.virt_humi,
                       v_light=self.virt_light,
                       v_cond=self.virt_cond,
                       )


ClusterFactory().registers(Model.MIFLORA, Protocol.HOMIE,
                           _ClusterMiflora)


class _ClusterSonoffSnzb01(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 countdown_short=60*5,
                 countdown_long=60*10,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_button = Button(self.friendly_name)
        self.virt_button.processor_append(ButtonTrigger(countdown_short=countdown_short,
                                                        countdown_long=countdown_long))
        self.declare_virtual_devices([self.virt_button])

    def enroll_device(self) -> MQTTBridge:
        return SonoffSnzb01(self.device_name,
                            v_button=self.virt_button)


ClusterFactory().registers(Model.ZB_BUTTON, Protocol.Z2M,
                           _ClusterSonoffSnzb01)


class _ClusterSonoffSnzb3(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 countdown=60*3,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_motion = Motion(self.friendly_name)
        self.virt_motion.processor_append(MotionTrigger(countdown=countdown))
        self.declare_virtual_devices([self.virt_motion])

    def enroll_device(self) -> MQTTBridge:
        return SonoffSnzb3(self.device_name,
                           v_motion=self.virt_motion)


ClusterFactory().registers(Model.ZB_MOTION, Protocol.Z2M,
                           _ClusterSonoffSnzb3)


class _ClusterNeoAlarm(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 v_alarm=None,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_alarm = v_alarm or Alarm(self.friendly_name,
                                           quiet_mode=False)
        self.declare_virtual_devices([self.virt_alarm])

    def enroll_device(self) -> MQTTBridge:
        return NeoNasAB02B2(self.device_name,
                            v_alarm=self.virt_alarm)


ClusterFactory().registers(Model.NEO_ALARM, Protocol.Z2M,
                           _ClusterNeoAlarm)


class _ClusterZBmini(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 countdown=60*3,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_switch = AutoStopSwitch(friendly_name=self.friendly_name,
                                          countdown=countdown)
        self.declare_virtual_devices([self.virt_switch])

    def enroll_device(self) -> MQTTBridge:
        return SonoffZbminiL(self.device_name,
                             v_switch=self.virt_switch)


ClusterFactory().registers(Model.ZB_MINI, Protocol.Z2M,
                           _ClusterZBmini)


class _ClusterZbSw02Right(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 countdown=60*3,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_switch = AutoStopSwitch(friendly_name=self.friendly_name,
                                          countdown=countdown)
        self.declare_virtual_devices([self.virt_switch])

    def enroll_device(self) -> MQTTBridge:
        return SonoffZbSw02Right(self.device_name,
                                 v_switch=self.virt_switch)


ClusterFactory().registers(Model.ZB_SW02, Protocol.Z2M,
                           _ClusterZbSw02Right)



class _ClusterUni(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 quiet_mode=False,
                 countdown=5,
                 v_adc=None,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        _prefix = self.friendly_name
        self.v_switch0 = AutoStopSwitch(friendly_name=_prefix + '_SW0',
                                        countdown=countdown)
        self.v_switch1 = AutoStopSwitch(friendly_name=_prefix + '_SW1',
                                        countdown=countdown)
        self.v_adc = v_adc or ADC(friendly_name=_prefix + '_ADC',
                                  quiet_mode=quiet_mode)
        self.declare_virtual_devices(
            [self.v_switch0, self.v_switch1, self.v_adc])

class _ClusterShellyUni(_ClusterUni):

    def enroll_device(self) -> MQTTBridge:
        return ShellyUni(self.device_name,
                         v_swit0=self.v_switch0,
                         v_swit1=self.v_switch1,
                         v_adc=self.v_adc)


ClusterFactory().registers(Model.SHELLY_UNI, Protocol.SHELLY,
                           _ClusterShellyUni)

class _ClusterTasmotaUni(_ClusterUni):

    def enroll_device(self) -> MQTTBridge:
        return TasmotaUni(self.device_name,
                         v_swit0=self.v_switch0,
                         v_swit1=self.v_switch1,
                         v_adc=self.v_adc)

ClusterFactory().registers(Model.SHELLY_UNI, Protocol.TASMOTA,
                           _ClusterTasmotaUni)


class _ClusterShellyPlugS(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 countdown=30,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        _prefix = self.friendly_name
        self.virt_switch = AutoStopSwitch(friendly_name=_prefix + '_SW0',
                                          countdown=countdown)
        self.declare_virtual_devices([self.virt_switch])

    def enroll_device(self) -> MQTTBridge:
        return ShellyPlugS(self.device_name,
                           v_swit0=self.virt_switch)


ClusterFactory().registers(Model.SHELLY_PLUGS, Protocol.SHELLY,
                           _ClusterShellyPlugS)

class _ClusterTasmotaPlugS(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 friendly_name=None,
                 quiet_mode=False,
                 countdown=30,
                 v_adc=None,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        _prefix = self.friendly_name
        self.virt_switch = AutoStopSwitch(friendly_name=_prefix + '_SW0',
                                          countdown=countdown)
        self.virt_temp = TemperatureSensor(friendly_name=_prefix + '_SW0')
        self.v_adc = v_adc or ADC(friendly_name=_prefix + '_ADC',
                                  quiet_mode=quiet_mode)
        self.declare_virtual_devices(
            [self.virt_switch, self.virt_temp, self.v_adc])

    def enroll_device(self) -> MQTTBridge:
        return TasmotaPlugS(self.device_name,
                            v_swit0=self.virt_switch,
                            v_temp=self.virt_temp,
                            v_adc=self.v_adc,
                            )


ClusterFactory().registers(Model.SHELLY_PLUGS, Protocol.TASMOTA,
                           _ClusterTasmotaPlugS)


class _ClusterRingCamera(Cluster):
    def __init__(self,
                 model: Model,
                 protocol: Protocol,
                 device_name: str,
                 location: str,
                 friendly_name=None,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.location = location
        self.virt_button = Button(self.friendly_name)
        self.virt_motion = Motion(self.friendly_name)
        self.declare_virtual_devices([self.virt_button, self.virt_motion])

    def enroll_device(self) -> MQTTBridge:
        return RingCamera(self.device_name,
                          self.location,
                          v_button=self.virt_button,
                          v_motion=self.virt_motion,
                          )


ClusterFactory().registers(Model.RING_CAMERA, Protocol.RING,
                           _ClusterRingCamera)
