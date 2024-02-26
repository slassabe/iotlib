#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.connectors.test_z2m
"""
import time
import unittest

from iotlib.bridge import EncodingException
from iotlib.client import MQTTClientBase
from iotlib.codec.z2m import DeviceOnZigbee2MQTT, SonoffSnzb02, SonoffSnzb01, SonoffSnzb3, NeoNasAB02B2, SonoffZbminiL
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               TemperatureSensor, VirtualDevice)

from ..utils import log_it, logger, get_broker_name
from ..mocks import MockSwitch

class TestDeviceOnZigbee2MQTT(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_device'

    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64,"linkquality":60,"temperature":19.6,"voltage":2900}'
    # PROPERTY_MESSAGE = b'{"humidity":64}'

    def test_init(self):
        log_it("Testing DeviceOnZigbee2MQTT init")
        mqtt_client = MQTTClientBase('', self.TARGET)
        zigbee_dev = DeviceOnZigbee2MQTT(mqtt_client,
                                         self.DEVICE_NAME,
                                         topic_base=self.TOPIC_BASE)
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()

    def test_decode_availability(self):
        log_it('Testing availability message handling')
        mqtt_client = MQTTClientBase('', self.TARGET)
        zigbee_dev = DeviceOnZigbee2MQTT(mqtt_client,
                                         self.DEVICE_NAME,
                                         topic_base=self.TOPIC_BASE)
        time.sleep(2)
        # Check ONLINE availability decodding
        zigbee_dev.client.publish(zigbee_dev.get_availability_topic(),
                                  'online')
        time.sleep(1)
        self.assertTrue(zigbee_dev.availability)
        # Check OFFLINE availability decodding
        zigbee_dev.client.publish(zigbee_dev.get_availability_topic(),
                                  'offline')
        time.sleep(1)
        self.assertFalse(zigbee_dev.availability)
        mqtt_client.stop()

    def test_decode_availability_fail(self):
        log_it('Testing availability message handling : FAIL')
        mqtt_client = MQTTClientBase('', self.TARGET)
        zigbee_dev = DeviceOnZigbee2MQTT(mqtt_client,
                                         self.DEVICE_NAME,
                                         topic_base=self.TOPIC_BASE)
        time.sleep(2)
        # Check ONLINE availability decodding
        zigbee_dev.client.publish(zigbee_dev.get_availability_topic(),
                                  'online')
        time.sleep(1)
        self.assertTrue(zigbee_dev.availability)
        # Try to decode error message
        with self.assertRaises(EncodingException) as ctx:
            zigbee_dev._decode_avail_pl(b'availability_format_error')

        # Check ONLINE availability decodding is unchanged
        self.assertTrue(zigbee_dev.availability)
        mqtt_client.stop()

    def test_decode_property(self):
        log_it('Testing property message handling WITHOUT backend')
        mqtt_client = MQTTClientBase('', self.TARGET)
        zigbee_dev = DeviceOnZigbee2MQTT(mqtt_client,
                                         self.DEVICE_NAME,
                                         topic_base=self.TOPIC_BASE)
        time.sleep(2)

        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.PROPERTY_MESSAGE)
        time.sleep(1)
        logger.warning(f"CANNOT DECODE VALUES WITHOUT BACKEND")

        self.assertEqual(zigbee_dev.decoded_values, [])
        mqtt_client.stop()

    def test_SonoffSnzb02(self):
        log_it('Testing SonoffSnzb02')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_temp = TemperatureSensor()
        v_humi = HumiditySensor()
        zigbee_dev = SonoffSnzb02(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_temp,
                                  v_humi,
                                  topic_base=self.TOPIC_BASE)
        time.sleep(2)
        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.PROPERTY_MESSAGE)
        time.sleep(1)
        logger.info(f"DECODED VALUES: {zigbee_dev.decoded_values}")
        mqtt_client.stop()


class TestSonoffSnzb02(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_device'

    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64.1,"linkquality":60,"temperature":19.6,"voltage":2900}'

    def test_end_point_decode(self):
        log_it('Testing SonoffSnzb02 end point decoder')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_temp = TemperatureSensor()
        v_humi = HumiditySensor()
        zigbee_dev = SonoffSnzb02(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_temp,
                                  v_humi,
                                  topic_base=self.TOPIC_BASE)
        payload = {'temperature': 25.5}
        result = zigbee_dev._decode_temp_pl(payload)
        self.assertEqual(result, 25.5)

        payload = {'humidity': 55}
        result = zigbee_dev._decode_humi_pl(payload)
        self.assertEqual(result, 55)
        mqtt_client.stop()

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb02 Sensor')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_temp = TemperatureSensor()
        v_humi = HumiditySensor()
        zigbee_dev = SonoffSnzb02(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_temp,
                                  v_humi,
                                  topic_base=self.TOPIC_BASE)
        time.sleep(2)

        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.PROPERTY_MESSAGE,
                                  )
        time.sleep(2)

        self.assertEqual(v_temp.value, 19.6)
        self.assertEqual(v_humi.value, 64)
        mqtt_client.stop()


class TestSonoffSnzb01(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_button'

    MESSAGE_SINGLE = b'{"action":"single","battery":100,"linkquality":164,"voltage":3000}'
    MESSAGE_DOUBLE = b'{"action":"double","battery":100,"linkquality":164,"voltage":3000}'
    MESSAGE_LONG = b'{"action":"long","battery":100,"linkquality":164,"voltage":3000}'

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb01 Sensor')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_button = Button()
        zigbee_dev = SonoffSnzb01(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_button,
                                  topic_base=self.TOPIC_BASE)
        time.sleep(2)
        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.MESSAGE_SINGLE,
                                  )
        time.sleep(1)
        self.assertEqual(v_button.value, 'single')

        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.MESSAGE_DOUBLE,
                                  )
        time.sleep(1)
        self.assertEqual(v_button.value, 'double')

        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.MESSAGE_LONG,
                                  )
        time.sleep(1)
        self.assertEqual(v_button.value, 'long')

        mqtt_client.stop()

    def test_FAIL01(self):
        log_it('Testing TestSonoffSnzb01 value message handling : FAIL')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_button = Button()
        zigbee_dev = SonoffSnzb01(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_button,
                                  topic_base=self.TOPIC_BASE)
        time.sleep(2)
        with self.assertRaises(EncodingException) as ctx:
            zigbee_dev._decode_values(zigbee_dev.get_subscription_list()[0],
                                  'value_format_error',
                                  )
        time.sleep(1)
        mqtt_client.stop()

    def test_FAIL02(self):
        log_it('Testing TestSonoffSnzb01 value message handling : FAIL')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_button = Button()
        zigbee_dev = SonoffSnzb01(mqtt_client,
                                  self.DEVICE_NAME,
                                  v_button,
                                  topic_base=self.TOPIC_BASE)
        time.sleep(2)
        with self.assertRaises(EncodingException) as ctx:
            zigbee_dev._decode_values(zigbee_dev.get_subscription_list()[0],
                                      b'{"action":"triple","battery":100,"linkquality":164,"voltage":3000}')
        mqtt_client.stop()


class TestSonoffSnzb3(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_motion'

    MESSAGE_FALSE = b'{"battery":64,"battery_low":false,"linkquality":144,"occupancy":false,"tamper":false,"voltage":2900}'
    MESSAGE_TRUE = b'{"battery":64,"battery_low":false,"linkquality":144,"occupancy":true,"tamper":false,"voltage":2900}'

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb3 Sensor')
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_motion = Motion()
        zigbee_dev = SonoffSnzb3(mqtt_client,
                                 self.DEVICE_NAME,
                                 v_motion,
                                 topic_base=self.TOPIC_BASE)
        time.sleep(2)
        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.MESSAGE_FALSE,
                                  )
        time.sleep(1)
        self.assertFalse(v_motion.value)

        zigbee_dev.client.publish(zigbee_dev.get_subscription_list()[0],
                                  self.MESSAGE_TRUE,
                                  )
        time.sleep(1)
        self.assertTrue(v_motion.value)
        mqtt_client.stop()

class TestNeoNasAB02B2(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_alarm'

    def test_init(self):
        log_it("Testing NasAB02B2 init")
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_alarm = Alarm()
        zigbee_dev = NeoNasAB02B2(mqtt_client,
                                 self.DEVICE_NAME,
                                 v_alarm,
                                 topic_base=self.TOPIC_BASE)
        
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()

    def X_test_start_and_stop(self):
        log_it("Testing NasAB02B2 init")
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_alarm = Alarm()
        zigbee_dev = NeoNasAB02B2(mqtt_client,
                                 self.DEVICE_NAME,
                                 v_alarm,
                                 topic_base=self.TOPIC_BASE)
        
        time.sleep(2)
        zigbee_dev.set_sound(melody = 10, alarm_level = 'low', alarm_duration = 2)
        zigbee_dev.change_state(is_on = True)
        time.sleep(1)
        self.assertTrue(v_alarm.value)

        mqtt_client.stop()

    
class TestSonoffZbminiL(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_switch'

    def test_init(self):
        log_it("Testing SonoffZbminiL init")
        mqtt_client = MQTTClientBase('', self.TARGET)
        v_switch = Switch()
        zigbee_dev = SonoffZbminiL(mqtt_client,
                                 self.DEVICE_NAME,
                                 v_switch,
                                 topic_base=self.TOPIC_BASE)
        
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()


    def test_start_and_stop(self):
        log_it("Testing SonoffZbminiL init")
        mqtt_client = MQTTClientBase('', self.TARGET)
        mock = MockSwitch(mqtt_client,
                          device_name=self.DEVICE_NAME,
                          topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        zigbee_dev = SonoffZbminiL(mqtt_client,
                                 self.DEVICE_NAME,
                                 v_switch,
                                 topic_base=self.TOPIC_BASE)
        
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        zigbee_dev.change_state(is_on = True)
        time.sleep(1)
        self.assertTrue(mock.state)
        self.assertTrue(v_switch.value)

        zigbee_dev.change_state(is_on = False)
        time.sleep(1)
        self.assertFalse(mock.state)
        self.assertFalse(v_switch.value)

        zigbee_dev.ask_for_state()
        time.sleep(1)
        self.assertFalse(v_switch.value)
        mqtt_client.stop()
