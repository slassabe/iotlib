#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_factory
"""


import time
import unittest

from .helper import get_broker_name, log_it, logger
from .mocks import MockZigbeeSensor, MockZigbeeSwitch, MockZigbeeMultiSwitch
from iotlib.bridge import DecodingException, MQTTBridge
from iotlib.client import MQTTClient
from iotlib.factory import CodecFactory, Model, Protocol
from iotlib.virtualdev import (HumiditySensor, TemperatureSensor, 
                               Switch, Switch0, Switch1)

TOPIC_BASE = 'TEST_A2IOT/factory'


class TestZ2MAirsensor(unittest.TestCase):
    target = get_broker_name()

    def X_test_Snzb02(self):
        DEVICE_NAME = 'fake_sensor'
        log_it("Testing Snzb02 : publish to mock")
        mqtt_client = MQTTClient('', get_broker_name())

        _mock = MockZigbeeSensor(mqtt_client,
                                device_name=DEVICE_NAME,
                                topic_base=TOPIC_BASE,
                                model = Model.ZB_AIRSENSOR)
        _v_temp=TemperatureSensor('temperature')
        _v_humi=HumiditySensor('humidity')
        _codec = CodecFactory().create_instance(model=Model.ZB_AIRSENSOR,
                                                 protocol=Protocol.Z2M,
                                                 device_name=DEVICE_NAME,
                                                 topic_base=TOPIC_BASE,
                                                 v_temp=_v_temp,
                                                 v_humi=_v_humi,
                                                 )
        bridge = MQTTBridge(mqtt_client, _codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)

        _mock.publish(temperature=20.0, humidity=50)
        time.sleep(1)
        self.assertEqual(_v_temp.value, 20.0)
        self.assertEqual(_v_humi.value, 50)
        mqtt_client.stop()

    def X_test_Ts0601Soil(self):
        DEVICE_NAME = 'fake_sensor'
        log_it("Testing Ts0601Soil : publish to mock")
        mqtt_client = MQTTClient('', get_broker_name())

        _mock = MockZigbeeSensor(mqtt_client,
                                device_name=DEVICE_NAME,
                                topic_base=TOPIC_BASE,
                                model = Model.TUYA_SOIL)
        _v_temp=TemperatureSensor('temperature')
        _v_humi=HumiditySensor('humidity')
        _codec = CodecFactory().create_instance(model=Model.TUYA_SOIL,
                                                 protocol=Protocol.Z2M,
                                                 device_name=DEVICE_NAME,
                                                 topic_base=TOPIC_BASE,
                                                 v_temp=_v_temp,
                                                 v_humi=_v_humi,
                                                 )
        bridge = MQTTBridge(mqtt_client, _codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)

        _mock.publish(temperature=30.0, humidity=60)
        time.sleep(1)
        self.assertEqual(_v_temp.value, 30.0)
        self.assertEqual(_v_humi.value, 60)
        mqtt_client.stop()

    def X_test_ZbminiL(self):
        DEVICE_NAME = 'fake_ZbminiL'
        log_it("Testing SonoffZbminiL : publish to mock")
        mqtt_client = MQTTClient('', get_broker_name())
        mock = MockZigbeeSwitch(mqtt_client,
                                device_name=DEVICE_NAME,
                                v_switch=Switch(),  # not used
                                topic_base=TOPIC_BASE)
        v_switch = Switch()
        _codec = CodecFactory().create_instance(model=Model.ZB_MINI,
                                                 protocol=Protocol.Z2M,
                                                 device_name=DEVICE_NAME,
                                                 topic_base=TOPIC_BASE,
                                                 v_switch=v_switch,
                                                 )

        bridge = MQTTBridge(mqtt_client, _codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        v_switch.trigger_change_state(bridge, is_on=True)
        time.sleep(1)
        self.assertTrue(mock.state)

        v_switch.trigger_change_state(bridge, is_on=False)

        time.sleep(1)
        self.assertFalse(mock.state)

        v_switch.trigger_get_state(bridge)
        time.sleep(1)
        self.assertFalse(mock.state)
        mqtt_client.stop()

    def test_ZbSw02(self):
        DEVICE_NAME = 'fake_ZbSw02'
        log_it("Testing eWeLink:ZB-SW02 : publish to mock")
        mqtt_client = MQTTClient('', get_broker_name())
        mock = MockZigbeeMultiSwitch(mqtt_client,
                                device_name=DEVICE_NAME,
                                v_switch0=Switch0(),  # not used
                                v_switch1=Switch1(),  # not used
                                topic_base=TOPIC_BASE)
        v_switch0 = Switch0('switch0')
        v_switch1 = Switch1('switch1')
        _codec = CodecFactory().create_instance(model=Model.EL_ZBSW02,
                                                 protocol=Protocol.Z2M,
                                                 device_name=DEVICE_NAME,
                                                 topic_base=TOPIC_BASE,
                                                 v_switch0=v_switch0,
                                                 v_switch1=v_switch1,
                                                 )
        bridge = MQTTBridge(mqtt_client, _codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)

        v_switch0.trigger_change_state(bridge, is_on=True)
        v_switch1.trigger_change_state(bridge, is_on=False)
        time.sleep(1)
        self.assertTrue(mock.state0)
        self.assertFalse(mock.state1)

        v_switch0.trigger_change_state(bridge, is_on=False)
        v_switch1.trigger_change_state(bridge, is_on=True)
        time.sleep(1)
        self.assertFalse(mock.state0)
        self.assertTrue(mock.state1)
        mqtt_client.stop()
