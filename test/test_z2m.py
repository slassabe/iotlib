#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_z2m
"""
import time
import unittest

from iotlib.bridge import DecodingException, MQTTBridge
from iotlib.processor import AvailabilityPublisher, AvailabilityLogger
from iotlib.client import MQTTClient
from iotlib.codec.z2m import DeviceOnZigbee2MQTT, SonoffSnzb02, SonoffSnzb01, SonoffSnzb3, NeoNasAB02B2, SonoffZbminiL
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               TemperatureSensor)

from .helper import log_it, logger, get_broker_name
from .mocks import MockZigbeeSwitch


class TestAvailabilityOnZigbee2MQTT(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'availability_device'

    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64,"linkquality":60,"temperature":19.6,"voltage":2900}'
    # PROPERTY_MESSAGE = b'{"humidity":64}'

    def test_init(self):
        log_it("Testing DeviceOnZigbee2MQTT init")
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()

    def test_decode_availability(self):
        log_it('Testing availability message handling')
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        # Check ONLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'online')
        time.sleep(1)
        self.assertTrue(bridge.availability)
        # Check OFFLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'offline')
        time.sleep(1)
        self.assertFalse(bridge.availability)
        mqtt_client.stop()

    def test_availability_logger_00(self):
        log_it("Testing TestAvailabilityLogger")
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        publisher = AvailabilityLogger(device_name=self.DEVICE_NAME)
        bridge.avail_proc_append(publisher)

        time.sleep(2)   # Wait MQTT client connection
        # Check ONLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'online')
        time.sleep(1)
        self.assertTrue(bridge.availability)
        # Check OFFLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'offline')
        time.sleep(1)
        self.assertFalse(bridge.availability)
        mqtt_client.stop()

    def test_availability_publisher_00(self):
        log_it("Testing TestAvailabilityLogger")
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        publisher = AvailabilityPublisher(device_name=self.DEVICE_NAME,
                                          client=mqtt_client,
                                          topic_base='TEST_A2IOT/canonical')
        bridge.avail_proc_append(publisher)

        time.sleep(2)   # Wait MQTT client connection
        # Check ONLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'online')
        time.sleep(1)
        self.assertTrue(bridge.availability)
        # Check OFFLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'offline')
        time.sleep(1)
        self.assertFalse(bridge.availability)
        mqtt_client.stop()

    def test_availability_publisher_01(self):
        log_it("Testing TestAvailabilityLogger - message lost")
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        publisher = AvailabilityPublisher(device_name='device_avail_lost',
                                          client=mqtt_client,
                                          topic_base='TEST_A2IOT/canonical')
        bridge.avail_proc_append(publisher)

        time.sleep(2)   # Wait MQTT client connection
        # Check ONLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'online')
        time.sleep(1)

    def test_decode_availability_fail(self):
        log_it('Testing availability message handling : FAIL')
        mqtt_client = MQTTClient('', self.TARGET)
        codec = DeviceOnZigbee2MQTT(device_name=self.DEVICE_NAME,
                                    base_topic=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        # Check ONLINE availability decodding
        bridge.client.publish(codec.get_availability_topic(),
                              'online')
        time.sleep(1)
        self.assertTrue(bridge.availability)
        # Try to decode error message
        with self.assertRaises(DecodingException) as ctx:
            codec.decode_avail_pl(b'availability_format_error')

        # Check ONLINE availability decodding is unchanged
        self.assertTrue(bridge.availability)
        mqtt_client.stop()


class TestSonoffSnzb02(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'fake_device'

    PROPERTY_MESSAGE = b'{"battery":67.5,"humidity":64.1,"linkquality":60,"temperature":19.6,"voltage":2900}'

    def test_end_point_decode(self):
        log_it('Testing SonoffSnzb02 end point decoder')
        mqtt_client = MQTTClient('', self.TARGET)
        v_temp = TemperatureSensor()
        v_humi = HumiditySensor()
        codec = SonoffSnzb02(self.DEVICE_NAME,
                             v_temp,
                             v_humi,
                             topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)

        payload = {'temperature': 25.5}
        result = codec._decode_temp_pl('dummy_topic', payload)
        self.assertEqual(result, 25.5)

        payload = {'humidity': 55}
        result = codec._decode_humi_pl('dummy_topic', payload)
        self.assertEqual(result, 55)
        mqtt_client.stop()

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb02 Sensor')
        mqtt_client = MQTTClient('', self.TARGET)
        v_temp = TemperatureSensor()
        v_humi = HumiditySensor()
        codec = SonoffSnzb02(self.DEVICE_NAME,
                             v_temp,
                             v_humi,
                             topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection

        bridge.client.publish(codec._root_topic,
                              self.PROPERTY_MESSAGE,
                              )
        time.sleep(2)

        self.assertEqual(v_temp.value, 19.6)
        self.assertEqual(v_humi.value, 64)
        mqtt_client.stop()


class TestSonoffSnzb01(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'fake_button'

    MESSAGE_SINGLE = b'{"action":"single","battery":100,"linkquality":164,"voltage":3000}'
    MESSAGE_DOUBLE = b'{"action":"double","battery":100,"linkquality":164,"voltage":3000}'
    MESSAGE_LONG = b'{"action":"long","battery":100,"linkquality":164,"voltage":3000}'

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb01 Sensor')

        mqtt_client = MQTTClient('TestSonoffSnzb01', self.TARGET)
        mqtt_client.client.enable_logger()
        v_button = Button()
        codec = SonoffSnzb01(self.DEVICE_NAME,
                             v_button,
                             topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        bridge.client.publish(codec._root_topic,
                              self.MESSAGE_SINGLE,
                              )
        time.sleep(2)
        self.assertEqual(v_button.value, 'single')

        bridge.client.publish(codec._root_topic,
                              self.MESSAGE_DOUBLE,
                              )
        time.sleep(1)
        self.assertEqual(v_button.value, 'double')

        bridge.client.publish(codec._root_topic,
                              self.MESSAGE_LONG,
                              )
        time.sleep(1)
        self.assertEqual(v_button.value, 'long')

        mqtt_client.stop()

    def test_FAIL01(self):
        log_it('Testing TestSonoffSnzb01 value message handling : FAIL')
        mqtt_client = MQTTClient('', self.TARGET)
        v_button = Button()
        codec = SonoffSnzb01(self.DEVICE_NAME,
                             v_button,
                             topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        with self.assertRaises(DecodingException) as ctx:
            bridge._handle_values(codec._root_topic,
                                  'value_format_error',
                                  )
        time.sleep(1)
        mqtt_client.stop()

    def test_FAIL02(self):
        log_it('Testing TestSonoffSnzb01 value message handling : FAIL')
        mqtt_client = MQTTClient('', self.TARGET)
        v_button = Button()
        codec = SonoffSnzb01(self.DEVICE_NAME,
                             v_button,
                             topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        with self.assertRaises(DecodingException) as ctx:
            bridge._handle_values(codec._root_topic,
                                  b'{"action":"triple","battery":100,"linkquality":164,"voltage":3000}')
        mqtt_client.stop()


class TestSonoffSnzb3(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'fake_motion'

    MESSAGE_FALSE = b'{"battery":64,"battery_low":false,"linkquality":144,"occupancy":false,"tamper":false,"voltage":2900}'
    MESSAGE_TRUE = b'{"battery":64,"battery_low":false,"linkquality":144,"occupancy":true,"tamper":false,"voltage":2900}'

    def test_end_to_end(self):
        log_it('Testing end to end handler mechanism on SonoffSnzb3 Sensor')
        mqtt_client = MQTTClient('', self.TARGET)
        v_motion = Motion()

        codec = SonoffSnzb3(self.DEVICE_NAME,
                            v_motion,
                            topic_base=self.TOPIC_BASE)
        bridge = MQTTBridge(mqtt_client, codec)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        bridge.client.publish(codec._root_topic,
                              self.MESSAGE_FALSE,
                              )
        time.sleep(1)
        self.assertFalse(v_motion.value)

        bridge.client.publish(codec._root_topic,
                              self.MESSAGE_TRUE,
                              )
        time.sleep(1)
        self.assertTrue(v_motion.value)
        mqtt_client.stop()


class TestNeoNasAB02B2(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'fake_alarm'

    def test_init(self):
        log_it("Testing NasAB02B2 init")
        mqtt_client = MQTTClient('', self.TARGET)
        v_alarm = Alarm()
        codec = NeoNasAB02B2(self.DEVICE_NAME,
                             v_alarm,
                             client=mqtt_client,
                             topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()

    def X_test_start_and_stop(self):
        # Mock is required !
        log_it("Testing NasAB02B2 change_state")
        mqtt_client = MQTTClient('', self.TARGET)
        v_alarm = Alarm()
        codec = NeoNasAB02B2(self.DEVICE_NAME,
                             v_alarm,
                             client=mqtt_client,
                             topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        codec.set_sound(melody=10, alarm_level='low', alarm_duration=2)
        codec.change_state(is_on=True)
        time.sleep(2)
        self.assertTrue(v_alarm.value)

        mqtt_client.stop()


class TestSonoffZbminiL(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST_A2IOT/z2m'
    DEVICE_NAME = 'fake_switch'

    def test_Switch_00(self):
        log_it("Testing SonoffZbminiL init")
        mqtt_client = MQTTClient('', self.TARGET)
        v_switch = Switch()
        codec = SonoffZbminiL(self.DEVICE_NAME,
                              v_switch,
                              client=mqtt_client,
                              topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        mqtt_client.stop()

    def test_Switch_01(self):
        log_it("Testing SonoffZbminiL : publish to mock")
        mqtt_client = MQTTClient('', self.TARGET)
        mock = MockZigbeeSwitch(mqtt_client,
                                device_name=self.DEVICE_NAME,
                                v_switch=Switch(),  # not used
                                topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        codec = SonoffZbminiL(self.DEVICE_NAME,
                              v_switch,
                              client=mqtt_client,
                              topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        codec.change_state(is_on=True)
        time.sleep(1)
        self.assertTrue(mock.state)

        codec.change_state(is_on=False)
        time.sleep(1)
        self.assertFalse(mock.state)

        codec.ask_for_state()
        time.sleep(1)
        self.assertFalse(mock.state)
        mqtt_client.stop()

    def test_Switch_02(self):
        log_it("Testing SonoffZbminiL : ZigbeeDevice.change_state to VirtualDevice.value")
        mqtt_client = MQTTClient('', self.TARGET)
        mock = MockZigbeeSwitch(mqtt_client,
                                device_name=self.DEVICE_NAME,
                                v_switch=Switch(),  # not used
                                topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        codec = SonoffZbminiL(self.DEVICE_NAME,
                              v_switch,
                              client=mqtt_client,
                              topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        codec.change_state(is_on=True)
        time.sleep(1)
        self.assertTrue(v_switch.value)

        codec.change_state(is_on=False)
        time.sleep(1)
        self.assertFalse(v_switch.value)

        codec.ask_for_state()
        time.sleep(1)
        self.assertFalse(v_switch.value)
        mqtt_client.stop()

    def test_Switch_03(self):
        log_it("Testing SonoffZbminiL : ZigbeeDevice.change_state to VirtualDevice.value")
        mqtt_client = MQTTClient('', self.TARGET)
        mock = MockZigbeeSwitch(mqtt_client,
                                device_name=self.DEVICE_NAME,
                                v_switch=Switch(),  # not used
                                topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        codec = SonoffZbminiL(self.DEVICE_NAME,
                              v_switch,
                              client=mqtt_client,
                              topic_base=self.TOPIC_BASE)

        bridge = MQTTBridge(mqtt_client, codec)

        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        v_switch.trigger_start(bridge)
        time.sleep(1)
        self.assertTrue(v_switch.value)

        v_switch.trigger_stop(bridge)
        time.sleep(1)
        self.assertFalse(v_switch.value)

        codec.ask_for_state()
        time.sleep(1)
        self.assertFalse(v_switch.value)
        mqtt_client.stop()