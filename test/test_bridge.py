#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_bridge
"""
import json
import unittest
import time
import iotlib.client

from iotlib.client import MQTTClientBase
from .helper import log_it, logger, get_broker_name
from .mocks import MockSurrogate

TOPIC_BASE = 'TEST_A2IOT/bridge'


class TestSurrogate(unittest.TestCase):
    target = get_broker_name()

    def test_connect(self):
        log_it(f"Testing connection to {self.target}")
        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()
        time.sleep(2)
        self.assertFalse(mqtt_client.connected)


    def test_handle_availability(self):
        log_it('Mock Zigbee codec and test availability message handling')
        mqtt_client = MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'fake_device_00'
        mock = MockSurrogate(mqtt_client, device_name,
                                topic_base=TOPIC_BASE)
        time.sleep(2)
        self.assertIsNone(mock.availability)

        mock.client.publish(mock._state_sub_topic, 'online')
        time.sleep(1)
        self.assertTrue(mock.availability)

        mock.client.publish(mock._state_sub_topic, 'offline')
        time.sleep(1)
        self.assertFalse(mock.availability)
        mqtt_client.stop()

    def test_handle_property(self):
        log_it('Mock Zigbee codec and test property message handling')
        def _encode(temperature, humidity):
            _properties = {"battery":67.5,
                "humidity":humidity,
                "linkquality":60,
                "temperature":temperature,
                "voltage":2900}
            return json.dumps(_properties)

        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'test_device'
        mock = MockSurrogate(mqtt_client, device_name,
                                topic_base=TOPIC_BASE)
        time.sleep(2)

        mock.client.publish(mock._root_sub_topic, _encode(temperature = 37.2, humidity = 100))

        time.sleep(1)
        self.assertEqual(mock.v_temp.value, 37.2)
        mqtt_client.stop()

class TestMultiClient(unittest.TestCase):
    target = get_broker_name()

    def X_test_handle_property(self):
        log_it('Mock Zigbee codec and test property message handling')
        def _encode(temperature, humidity):
            _properties = {"battery":67.5,
                "humidity":humidity,
                "linkquality":60,
                "temperature":temperature,
                "voltage":2900}
            return json.dumps(_properties)

        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        mock = MockZigbeeMagic(mqtt_client, 
                                device_name=None,
                                topic_base=TOPIC_BASE)
        time.sleep(2)

        mock.client.publish(TOPIC_BASE + '/device00', _encode(temperature = 37.2, humidity = 100))

        time.sleep(1)
        self.assertEqual(mock.v_temp.value, 37.2)
        mqtt_client.stop()
