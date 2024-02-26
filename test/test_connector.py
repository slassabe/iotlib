#!/usr/local/bin/python3
# coding=utf-8

"""Client connector

$ source .venv/bin/activate
$ python -m unittest test.test_connector
"""

import inspect
import unittest
import time
from iotlib.client import MQTTClientBase
from iotlib.bridge import Connector
import iotlib.virtualdev

from .utils import log_it, logger, get_broker_name

class MockProtocole(Connector):
    def __init__(self, client: MQTTClientBase, device_name: str):
        super().__init__(client, device_name)
        self._set_message_handler(self.PROPERTY_TOPIC,
                          self.__class__._decode_property_pl,
                          iotlib.virtualdev.HumiditySensor(friendly_name='fake'),
                          'node')

    AVAILABILITY_TOPIC = 'TEST/CONNECTOR/device_name/availability'
    AVAILABILITY_MESSAGE = 'online'
    AVAILABILITY_VALUE = True
    def get_availability_topic(self) -> str:
        return self.AVAILABILITY_TOPIC
    def _decode_avail_pl(self, payload: str) -> bool:
        return self.AVAILABILITY_VALUE
    
    PROPERTY_TOPIC = 'TEST/CONNECTOR/device_name'
    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64,"linkquality":60,"temperature":19.6,"voltage":2900}'
    PROPERTY_VALUE = [('node', 'humidity', 100)]
    def get_subscription_list(self) -> list:
        return [self.PROPERTY_TOPIC]
    #def _decode_values(self, topic: str, payload: str) -> list:
    #    return self.PROPERTY_VALUE
    def _decode_property_pl(self, topic: str, payload: str) -> list:
        return 100

class TestConnector(unittest.TestCase):
    target = get_broker_name()

    def X_test_connected(self):
        log_it("Testing Connector init")
        mqtt_client = MQTTClientBase('', self.target)
        mock = MockProtocole(mqtt_client, 'fake_device')
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)

    def test_decode_property_pl(self):
        log_it("Testing Connector decode_property_pl")
        mqtt_client = MQTTClientBase('', self.target)
        mock = MockProtocole(mqtt_client, 'device_name')
        time.sleep(3)
        mock.client.publish(mock.PROPERTY_TOPIC,
                            mock.PROPERTY_MESSAGE)
        time.sleep(3)
        logger.info(f"decoded_values: {mock.decoded_values}")
        self.assertEqual(sorted(mock.decoded_values),
                         sorted(mock.PROPERTY_VALUE))
        mqtt_client.stop()