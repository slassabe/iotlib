#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_bridge
"""
import json
import unittest
import time
import iotlib.client

from iotlib.client import MQTTClient
from .helper import log_it, logger, get_broker_name
from .mocks import MockBridge

TOPIC_BASE = 'TEST_A2IOT/bridge'


class TestSurrogate(unittest.TestCase):
    target = get_broker_name()

    def test_connect(self):
        log_it(f"Testing connection to {self.target}")
        mqtt_client = iotlib.client.MQTTClient('', self.target)
        mqtt_client.start()
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()
        time.sleep(2)
        self.assertFalse(mqtt_client.connected)

    def test_handle_availability(self):
        log_it('Mock Zigbee codec and test availability message handling')
        mqtt_client = MQTTClient('', self.target)
        mqtt_client.start()

        device_name = 'fake_device_00'
        mock = MockBridge(mqtt_client, device_name,
                          topic_base=TOPIC_BASE)
        time.sleep(2)
        self.assertIsNone(mock.surrogate.availability)

        mock.surrogate.client.publish(mock.codec.state_topic, 'online')
        time.sleep(1)
        self.assertTrue(mock.surrogate.availability)

        mock.surrogate.client.publish(mock.codec.state_topic, 'offline')
        time.sleep(1)
        self.assertFalse(mock.surrogate.availability)
        mqtt_client.stop()

    def test_handle_property(self):
        log_it('Mock Zigbee codec and test property message handling')

        def _encode(temperature, humidity):
            _properties = {"battery": 67.5,
                           "humidity": humidity,
                           "linkquality": 60,
                           "temperature": temperature,
                           "voltage": 2900}
            return json.dumps(_properties)

        mqtt_client = iotlib.client.MQTTClient('', self.target)
        mqtt_client.start()

        device_name = 'test_device'
        mock = MockBridge(mqtt_client, device_name,
                          topic_base=TOPIC_BASE)
        time.sleep(2)

        mock.surrogate.client.publish(mock.codec.property_topic,
                                      _encode(temperature=37.2, humidity=100))

        time.sleep(1)
        self.assertEqual(mock.codec.v_temp.value, 37.2)
        mqtt_client.stop()


class TestMultiClient(unittest.TestCase):
    target = get_broker_name()

    def X_test_handle_property(self):
        log_it('Mock Zigbee codec and test property message handling')

        def _encode(temperature, humidity):
            _properties = {"battery": 67.5,
                           "humidity": humidity,
                           "linkquality": 60,
                           "temperature": temperature,
                           "voltage": 2900}
            return json.dumps(_properties)

        mqtt_client = iotlib.client.MQTTClient('', self.target)
        mqtt_client.start()

        mock = MockZigbeeMagic(mqtt_client,
                               device_name=None,
                               topic_base=TOPIC_BASE)
        time.sleep(2)

        mock.surrogate.client.publish(
            TOPIC_BASE + '/device00', _encode(temperature=37.2, humidity=100))

        time.sleep(1)
        self.assertEqual(mock.v_temp.value, 37.2)
        mqtt_client.stop()
