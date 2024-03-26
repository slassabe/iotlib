#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_real_z2m
"""
import time
import unittest

from iotlib.bridge import DecodingException, MQTTBridge
from iotlib.processor import AvailabilityPublisher, AvailabilityLogger
from iotlib.client import MQTTClient
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               TemperatureSensor)

from .helper import log_it, logger, get_broker_name
from iotlib.factory import CodecFactory, Model, Protocol


class TestRealZ2M(unittest.TestCase):
    TARGET = 'groseille.back.internal'
    def test_SonoffZbminiL(self):
        log_it("Testing SonoffZbminiL for real")
        client = MQTTClient('', self.TARGET)
        v_switch = Switch()
        _codec = CodecFactory().create_instance(model=Model.ZB_MINI,
                                                 protocol=Protocol.Z2M,
                                                 device_name='SWITCH_CAVE',
                                                 #topic_base=TOPIC_BASE,
                                                 v_switch=v_switch,
                                                 )

        bridge = MQTTBridge(client, _codec)

        client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(client.connected)
        v_switch.trigger_change_state(bridge, is_on=False)
        time.sleep(1)
        v_switch.trigger_change_state(bridge, is_on=True, on_time=3)
        #v_switch.trigger_change_state(bridge, is_on=True)
