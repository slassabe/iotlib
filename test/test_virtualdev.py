#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Virtual Device test

$ source .venv/bin/activate
$ python -m unittest test.test_virtualdev
"""
import unittest

from iotlib.virtualdev import HumiditySensor, VirtualDeviceProcessor

from .helper import log_it, logger

class Replicator(VirtualDeviceProcessor):
    """Replicates updates from virtual devices for testing purpose"""
    def __init__(self) -> None:
        super().__init__()
        self.property = None
        self.value = None

    def process_value_update(self, v_dev, bridge) -> None:
        self.property = v_dev.get_property()
        logger.debug("vdev property is : %s",
                      v_dev.get_property())
        self.value = v_dev.value

class TestVirtualDevice(unittest.TestCase):

    def test_set_value(self):
        log_it("Testing VirtualDevice set_value")
        _vdev = HumiditySensor(friendly_name='fake')
        _vdev.handle_value(100, bridge=None)

        self.assertEqual(_vdev.value, 100)
        self.assertEqual(_vdev.get_property().property_name, 'humidity')
        self.assertEqual(_vdev.get_property().property_node, 'sensor')

    def test_processor(self):
        log_it("Testing VirtualDevice processor")
        _vdev = HumiditySensor(friendly_name='fake')
        _replicator = Replicator()
        _vdev.value = 0
        _vdev.processor_append(_replicator)

        _vdev.handle_value(100, bridge=None)
        self.assertEqual(_replicator.property, _vdev.get_property())
        self.assertEqual(_replicator.value, 100)