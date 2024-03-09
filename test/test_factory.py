#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_factory
"""


import json
import unittest
import time
import iotlib.client
from iotlib.factory import ClusterFactory, Model, Protocol

from iotlib.client import MQTTClient
from .helper import log_it, logger, get_broker_name
from .mocks import MockBridge

TOPIC_BASE = 'TEST_A2IOT/factory'


class TestFactory(unittest.TestCase):
    target = get_broker_name()

    def X_test_init(self):
        log_it(f"Testing connection to {self.target}")
        mqtt_client = iotlib.client.MQTTClient('', self.target)
        mqtt_client.start()
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)

        _inst = ClusterFactory().create_instance(model=Model.ZB_AIRSENSOR,
                                                 protocol=Protocol.Z2M,
                                                 client=mqtt_client,
                                                 device_name='fake_device',
                                                 friendly_name='My_friend',
                                                 quiet_mode=True,
                                                 )
