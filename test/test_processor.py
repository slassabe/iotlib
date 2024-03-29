#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Virtual Device test

$ source .venv/bin/activate
$ python -m unittest test.test_processor
"""
import unittest
import time
from iotlib.virtualdev import ResultType
from iotlib.processor import (ButtonTrigger, MotionTrigger, PropertyPublisher)
from iotlib.devconfig import ButtonValues
from iotlib.client import MQTTClient
from iotlib.virtualdev import (ADC, Alarm, Button, HumiditySensor, 
                               Motion, Switch, TemperatureSensor)

from .helper import log_it, logger, get_broker_name

TOPIC_BASE = 'TEST_A2IOT/canonical'

class UnpluggedSwitch(Switch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started = None
    def trigger_start(self, client, on_time: int | None = None) -> bool:
        self.started = True
    def trigger_stop(self, client, on_time: int | None = None) -> bool:
        self.started = False

class UnpluggedAlarm(Alarm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started = None
    def trigger_start(self, client, on_time: int | None = None) -> bool:
        self.started = True
    def trigger_stop(self, client, on_time: int | None = None) -> bool:
        self.started = False

class TestMotionTrigger(unittest.TestCase):
    def test_motion_00(self):
        log_it("Testing MotionTrigger with unplugged switch")
        virt_switch = UnpluggedSwitch("fake_switch_00")
        virt_motion = Motion("fake_motion_00")
        virt_motion.processor_append(MotionTrigger(client=None))
        virt_motion.add_observer(virt_switch)

        self.assertIsNone(virt_motion.value)
        self.assertIsNone(virt_switch.started)

        _result = virt_motion.handle_value(True)
        self.assertTrue(_result == ResultType.SUCCESS)
        self.assertTrue(virt_motion.value)
        self.assertTrue(virt_switch.started)


class TestButtonTrigger(unittest.TestCase):
    def test_button_00(self):
        log_it("Testing ButtonTrigger with unplugged switch")
        virt_switch = UnpluggedSwitch("fake_switch_00")
        virt_button = Button("fake_button_00")
        virt_button.processor_append(ButtonTrigger(client=None))
        virt_button.add_observer(virt_switch)

        self.assertIsNone(virt_button.value)
        self.assertIsNone(virt_switch.started)

        _result = virt_button.handle_value(ButtonValues.SINGLE_ACTION.value)
        self.assertTrue(_result == ResultType.SUCCESS)
        self.assertTrue(virt_button.value == ButtonValues.SINGLE_ACTION.value)
        self.assertTrue(virt_switch.started)

        _result = virt_button.handle_value(ButtonValues.LONG_ACTION.value)
        self.assertTrue(_result == ResultType.SUCCESS)
        self.assertTrue(virt_button.value == ButtonValues.LONG_ACTION.value)
        self.assertFalse(virt_switch.started)


class TestPropertyPublisher(unittest.TestCase):
    def test_property_publisher_00(self):
        log_it("Testing PropertyPublisher")

        mqtt_publisher = MQTTClient('', get_broker_name())
        mqtt_publisher.start()
        time.sleep(2)

        publisher = PropertyPublisher(client=mqtt_publisher, publish_topic_base=TOPIC_BASE)

        virt_temperature = TemperatureSensor("fake_sensor")
        virt_temperature.processor_append(publisher)
        virt_temperature.handle_value(37.2)

        virt_temperature = HumiditySensor("fake_sensor")
        virt_temperature.processor_append(publisher)
        virt_temperature.handle_value(100)

        virt_button = Button("fake_button")
        virt_button.processor_append(publisher)
        virt_button.handle_value(ButtonValues.LONG_ACTION.value)

        virt_motion = Motion("fake_motion")
        virt_motion.processor_append(publisher)
        virt_motion.handle_value(True)

        virt_controler = ADC("fake_controler")
        virt_controler.processor_append(publisher)
        virt_controler.handle_value(12.1)

        virt_alarm = UnpluggedAlarm("fake_alarm")
        virt_alarm.processor_append(publisher)
        virt_alarm.handle_value(True)

        virt_alarm = UnpluggedSwitch("fake_switch")
        virt_alarm.processor_append(publisher)
        virt_alarm.handle_value(True)

        time.sleep(1)
        mqtt_publisher.stop()
