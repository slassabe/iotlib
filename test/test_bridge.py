#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_bridge
"""

import unittest
import time
import iotlib.client
from iotlib.bridge import Surrogate

from .utils import log_it, get_broker_name

class MockSurrogate(Surrogate):

    AVAILABILITY_TOPIC = 'TEST_A2IOT/test_device/availability'
    AVAILABILITY_MESSAGE = 'online'
    AVAILABILITY_VALUE = True
    def get_availability_topic(self) -> str:
        return self.AVAILABILITY_TOPIC
    def _decode_avail_pl(self, payload: str) -> bool:
        return self.AVAILABILITY_VALUE
    
    PROPERTY_TOPIC = 'zigbee2mqtt/TEMP_SALON'
    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64,"linkquality":60,"temperature":19.6,"voltage":2900}'
    PROPERTY_VALUE = [('sensor', 'humidity', 64), ('sensor', 'temperature', 19.6)]
    def get_subscription_list(self) -> list:
        return [self.PROPERTY_TOPIC]
    def _decode_values(self, topic: str, payload: str) -> list:
        return self.PROPERTY_VALUE
    

class TestSurrogate(unittest.TestCase):
    # target = 'groseille.back.internal'
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

    def test_init(self):
        log_it(f'Testing init Surrogate')
        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'test_device'
        b = MockSurrogate(mqtt_client, device_name)
        time.sleep(2)

        self.assertEqual(b.device_name, device_name)
        self.assertEqual(b.client, mqtt_client)
        mqtt_client.stop()

    def test_handle_availability(self):
        log_it(f'Testing availability message handling')
        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'test_device'
        mock = MockSurrogate(mqtt_client, device_name)
        time.sleep(2)

        mock.client.publish(mock.AVAILABILITY_TOPIC, 
                            mock.AVAILABILITY_MESSAGE)
        time.sleep(1)
        self.assertTrue(mock.availability)
        mqtt_client.stop()
    
    def test_handle_property(self):
        log_it(f'Testing property message handling')
        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'test_device'
        mock = MockSurrogate(mqtt_client, device_name)
        time.sleep(2)

        mock.client.publish(mock.PROPERTY_TOPIC,
                            mock.PROPERTY_MESSAGE)
        
        time.sleep(1)
        self.assertEqual(sorted(mock.decoded_values),
                         sorted(mock.PROPERTY_VALUE))
        mqtt_client.stop()