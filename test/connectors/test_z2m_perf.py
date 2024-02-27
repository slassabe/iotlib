#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.connectors.test_z2m_perf
"""
import time
import unittest
import time

from iotlib.bridge import DecodingException
from iotlib.client import MQTTClientBase
from iotlib.codec.z2m import DeviceOnZigbee2MQTT, SonoffSnzb02, SonoffSnzb01, SonoffSnzb3, NeoNasAB02B2, SonoffZbminiL
from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                               TemperatureSensor, VirtualDevice)
from iotlib.processor import VirtualDeviceProcessor

from ..utils import log_it, logger, get_broker_name
from ..mocks import MockSwitch


class FlipFlopMessage(VirtualDeviceProcessor):
    MAX_LOOP = 1000000

    def __init__(self, loop_in: bool = False) -> None:
        self.loop_count = 0
        self.loop_in = loop_in

    def handle_device_update(self, v_dev: Switch) -> None:
        logger.debug('[%s] logging device "%s" (property : "%s" - value : "%s")',
                     self,
                     v_dev,
                     v_dev.get_property(),
                     v_dev.value)
        if not self.loop_in:
            return
        if self.loop_count > self.MAX_LOOP:
            raise RuntimeError('Max loop exceeded')
        self.loop_count += 1
        if v_dev.value:
            v_dev.trigger_stop()
        else:
            v_dev.trigger_start()


class TestSonoffZbminiL(unittest.TestCase):
    TARGET = get_broker_name()

    TOPIC_BASE = 'TEST/z2m'
    DEVICE_NAME = 'fake_switch'

    def test_Switch_00(self):
        log_it("Testing SonoffZbminiL : no loop to check connection")
        mqtt_client = MQTTClientBase('', self.TARGET)
        mock = MockSwitch(mqtt_client,
                          device_name=self.DEVICE_NAME,
                          topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        v_switch.processor_append(FlipFlopMessage())  # No loop

        zigbee_dev = SonoffZbminiL(mqtt_client,
                                   self.DEVICE_NAME,
                                   v_switch,
                                   topic_base=self.TOPIC_BASE)
        mqtt_client.start()

        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)

        time.sleep(1)
        self.assertFalse(v_switch.value)    # Default value is False

        v_switch.trigger_start()
        time.sleep(1)
        self.assertTrue(v_switch.value)

        v_switch.trigger_stop()
        time.sleep(1)
        self.assertFalse(v_switch.value)

        mqtt_client.stop()

    def test_Switch_01(self):
        TEST_DURATION = 10 # sec.
        log_it("Testing SonoffZbminiL : publish, decode and access vdev")
        mqtt_client = MQTTClientBase('', self.TARGET)
        mock = MockSwitch(mqtt_client,
                          device_name=self.DEVICE_NAME,
                          topic_base=self.TOPIC_BASE)
        v_switch = Switch()
        zigbee_dev = SonoffZbminiL(mqtt_client,
                                   self.DEVICE_NAME,
                                   v_switch,
                                   topic_base=self.TOPIC_BASE)
        mqtt_client.start()
        time.sleep(2)   # Wait MQTT client connection
        self.assertTrue(mqtt_client.connected)
        # Add processing
        message_handler = FlipFlopMessage(loop_in=True)
        v_switch.processor_append(message_handler)

        _exc_start = time.perf_counter()
        _process_start = time.process_time_ns()
        v_switch.trigger_start()
        time.sleep(TEST_DURATION)
        _process_end = time.process_time_ns()
        _exc_end = time.perf_counter()

        _exec_delta = _exc_end - _exc_start
        _process_delta = (_process_end - _process_start) / 1000000  # millisec.
        _nb_message = message_handler.loop_count * 2
        logger.warning(f"MQTT brocker : {get_broker_name()} - "
                    f"{_nb_message} loops in {_exec_delta:.2f}s"
                    f" -> {_nb_message / (_exec_delta):.2f} messages/s"
                    f" - {_process_delta:.2f} ms")
        self.assertTrue(message_handler.loop_count > 1)
        mqtt_client.stop()
