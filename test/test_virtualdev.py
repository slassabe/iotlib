#!/usr/local/bin/python3
# coding=utf-8

"""Virtual Device test

$ source .venv/bin/activate
$ python -m unittest test.test_virtauldev
"""
import inspect
import unittest
import time
import iotlib.virtualdev
import iotlib.processor
import iotlib.devconfig

from .utils import log_it, logger

class Replicator(iotlib.processor.VirtualDeviceProcessor):
    """Replicates updates from virtual devices for testing purpose"""
    def __init__(self) -> None:
        super().__init__()
        self.property = None
        self.value = None

    def handle_device_update(self, v_dev) -> None:
        self.property = v_dev.get_property()
        logger.debug("vdev property is : %s",
                      v_dev.get_property())
        self.value = v_dev.value

class TestVirtualDevice(unittest.TestCase):

    def test_init(self):
        log_it("Testing VirtualDevice init")
        _dummy = iotlib.virtualdev.HumiditySensor(friendly_name='fake')
        self.assertIsNone(_dummy.value)
    
    def test_set_value(self):
        log_it("Testing VirtualDevice set_value")
        _vdev = iotlib.virtualdev.HumiditySensor(friendly_name='fake')
        _vdev.value = 100
        self.assertEqual(_vdev.value, 100)

    def test_processor(self):
        log_it("Testing VirtualDevice processor")
        _vdev = iotlib.virtualdev.HumiditySensor(friendly_name='fake')
        _replicator = Replicator()
        _vdev.value = 100
        _vdev.processor_append(_replicator)

        _vdev._on_event()
        self.assertEqual(_replicator.property, _vdev.get_property())
        self.assertEqual(_replicator.value, 100)