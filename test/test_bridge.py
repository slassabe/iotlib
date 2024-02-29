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
from iotlib.virtualdev import (HumiditySensor, TemperatureSensor)

from iotlib.bridge import Surrogate, DecodingException
from iotlib.client import MQTTClient
from .helper import log_it, get_broker_name

TOPIC_BASE = 'TEST_A2IOT/bridge'


class MockZigbeeSensor(Surrogate):

    def __init__(self,
                 mqtt_client: MQTTClient,
                 device_name: str,
                 topic_base: str = None):
        self._root_sub_topic = f'{topic_base}/{device_name}'
        self._state_sub_topic = f'{topic_base}/{device_name}/availability'
        super().__init__(mqtt_client, device_name=device_name)

        self.availability = None
        self.v_temp = TemperatureSensor()
        self.v_humi = HumiditySensor()
        self._set_message_handler(self._root_sub_topic,
                                  self.__class__._decode_temp_pl,
                                  self.v_temp)
        self._set_message_handler(self._root_sub_topic,
                                  self.__class__._decode_humi_pl,
                                  self.v_humi)

    def get_availability_topic(self) -> str:
        return self._state_sub_topic

    def _decode_avail_pl(self, payload: str) -> bool:
        if payload != 'online' and payload != 'offline' and payload is not None:
            raise DecodingException(f'Payload value error: {payload}')
        else:
            return payload == 'online'


    def _decode_temp_pl(self, topic, payload: dict) -> float:
        _value = json.loads(payload).get(('temperature'))
        if _value is None:
            raise DecodingException(
                f'No "temperature" key in payload : {payload}')
        else:
            return float(_value)

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = json.loads(payload).get('humidity')
        if _value is None:
            raise DecodingException(
                f'No "humidity" key in payload : {payload}')
        else:
            return int(_value)
    
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
        mqtt_client = iotlib.client.MQTTClientBase('', self.target)
        mqtt_client.start()

        device_name = 'fake_device_00'
        mock = MockZigbeeSensor(mqtt_client, device_name,
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
        mock = MockZigbeeSensor(mqtt_client, device_name,
                                topic_base=TOPIC_BASE)
        time.sleep(2)

        mock.client.publish(mock._root_sub_topic, _encode(temperature = 37.2, humidity = 100))

        time.sleep(1)
        self.assertEqual(mock.v_temp.value, 37.2)
        mqtt_client.stop()
