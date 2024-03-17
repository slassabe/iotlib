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

from iotlib.client import MQTTClient
from iotlib.bridge import MQTTBridge
from iotlib.codec.core import Codec
from iotlib.codec.z2m import (NeoNasAB02B2, SonoffSnzb01, SonoffSnzb02, SonoffSnzb3,
                              SonoffZbminiL, Ts0601Soil, SonoffZbSw02Right)
from iotlib.processor import (PropertyPublisher, VirtualDeviceLogger,
                              ButtonTrigger, AvailabilityLogger, AvailabilityPublisher, MotionTrigger)

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
                 friendly_name: str = None,
                 ):
        self.model: Model = model
        self.protocol: Protocol = protocol,
        self.device_name = device_name
        self.friendly_name = friendly_name or device_name
        self.codec = None

    def declare_virtual_devices(self, virtual_devices: List[VirtualDevice]):
        for virt_dev in virtual_devices:
            assert isinstance(virt_dev, VirtualDevice),  \
                f"Item {virt_dev} is not a VirtualDevice instance"
            virt_dev.processor_append(VirtualDeviceLogger())
            # This will publish property changes on MQTT
            virt_dev.processor_append(PropertyPublisher(client=mqqtt_from_somewhere,
                                                        publish_topic_base=topic_base_from_somewhere))

    @abstractmethod
    def get_codec(self) -> Codec:
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

    def registers(self,
                  model: Model,
                  protocol: Protocol,
                  constructor: Callable[[list], Cluster]) -> None:
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

    def _get_constructor(self, model: str, protocol=None) -> Callable[[list], Cluster]:
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

    def create_instance(self,
                        model: Model,
                        protocol: Protocol,
                        client: MQTTClient,
                        device_name: str,
                        *args, **kwargs) -> Cluster:
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
        def _set_availability_processors(bridge: MQTTBridge,
                                         device_name: str):
            # This will log availability changes
            bridge.add_availability_processor(AvailabilityLogger(device_name))
            # This will publish availability changes on MQTT
            bridge.add_availability_processor(
                AvailabilityPublisher(device_name, bridge.client))
            # Silent mode:
            # self.property_proc_append(PropertyLogger())

        if not isinstance(model, Model):
            raise TypeError(f"Model {model} is not of type Model")
        if not isinstance(protocol, Protocol):
            raise TypeError(f"Protocole {protocol} is not of type Protocol")
        if not isinstance(client, MQTTClient):
            raise TypeError(f"Bad type for Client {client} : {type(client)}")

        _constructor = self._get_constructor(model, protocol)
        _cluster = _constructor(model, protocol, device_name, *args, **kwargs)
        #
        _cluster.codec = _cluster.get_codec()
        _set_availability_processors(_cluster.codec, device_name)

        MQTTBridge(client, _cluster.codec)

        return _cluster


# Device customization

class _ClusterAirSensor(Cluster):
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


class _ClusterSonoffSnzb02(_ClusterAirSensor):
    def get_codec(self) -> Codec:
        return SonoffSnzb02(self.device_name,
                            v_temp=self.virt_temp,
                            v_humi=self.virt_humi,
                            )


ClusterFactory().registers(Model.ZB_AIRSENSOR, Protocol.Z2M,
                           _ClusterSonoffSnzb02)


class _ClusterTs0601Soil(_ClusterAirSensor):
    def get_codec(self) -> Codec:
        return Ts0601Soil(self.device_name,
                          v_temp=self.virt_temp,
                          v_humi=self.virt_humi,
                          )


ClusterFactory().registers(Model.TUYA_SOIL, Protocol.Z2M,
                           _ClusterTs0601Soil)


class _ClusterMiflora(_ClusterAirSensor):
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

    def get_codec(self) -> Codec:
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
                 countdown_long=60*10,
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_button = Button(self.friendly_name)
        self.virt_button.processor_append(
            ButtonTrigger(countdown_long=countdown_long))
        self.declare_virtual_devices([self.virt_button])

    def get_codec(self) -> Codec:
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
                 ):
        super().__init__(model, protocol, device_name, friendly_name)
        self.virt_motion = Motion(self.friendly_name)
        self.virt_motion.processor_append(MotionTrigger())
        self.declare_virtual_devices([self.virt_motion])

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
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
        self.virt_switch = Switch(friendly_name=self.friendly_name,
                                  countdown=countdown)
        self.declare_virtual_devices([self.virt_switch])

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
        return ShellyUni(self.device_name,
                         v_swit0=self.v_switch0,
                         v_swit1=self.v_switch1,
                         v_adc=self.v_adc)


ClusterFactory().registers(Model.SHELLY_UNI, Protocol.SHELLY,
                           _ClusterShellyUni)


class _ClusterTasmotaUni(_ClusterUni):

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
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

    def get_codec(self) -> Codec:
        return RingCamera(self.device_name,
                          self.location,
                          v_button=self.virt_button,
                          v_motion=self.virt_motion,
                          )


ClusterFactory().registers(Model.RING_CAMERA, Protocol.RING,
                           _ClusterRingCamera)
