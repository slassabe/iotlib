#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_discoverer
"""
import unittest
import time
from .helper import get_broker_name, log_it, logger
from iotlib.abstracts import DiscoveryProcessor
from iotlib.bridge import MQTTBridge
from iotlib.client import MQTTClient
from iotlib.discoverer import ZigbeeDiscoverer, TasmotaDiscoverer, UnifiedDiscoverer
from iotlib.factory import CodecFactory, Model, Protocol
from iotlib.processor import AvailabilityLogger


class BasicDiscoveryProc(DiscoveryProcessor):
    def __init__(self) -> None:
        super().__init__()
        self.nb_devices = None
    def process_discovery_update(self, devices):
        self.nb_devices = len(devices)
        logger.debug(f"Discovered {len(devices)} devices")
        for device in devices:
            logger.debug(f"Device: {device}")


class ExtendedDiscoveryProc(DiscoveryProcessor):
    def __init__(self, mqtt_client: MQTTClient) -> None:
        super().__init__()
        self.mqtt_client = mqtt_client

    def process_discovery_update(self, devices):
        logger.info(f"Discovered {len(devices)} devices")
        for device in devices:
            _codec = CodecFactory().create_instance(model=device.model,
                                                    protocol=device.protocol,
                                                    device_name=device.friendly_name)
            _bridge = MQTTBridge(self.mqtt_client, _codec)
            _logger = AvailabilityLogger(debug=True)
            _bridge.add_availability_processor(_logger)
        self.mqtt_client.start()


class TestDiscoZ2M(unittest.TestCase):
    TARGET = 'groseille.back.internal'
    def test_discoverer01(self):
        log_it("Testing Zigbee Discoverer")
        client = MQTTClient('', self.TARGET)
        _discoverer = ZigbeeDiscoverer(client)
        client.start()
        time.sleep(2)
        logger.debug(_discoverer.get_devices())
        self.assertGreater(len(_discoverer.get_devices()), 0)
        client.disconnect()

    def test_discoverer02(self):
        log_it("Testing Zigbee Discoverer with processor")
        client = MQTTClient('', self.TARGET)
        _discoverer = ZigbeeDiscoverer(client)
        _disco_process = BasicDiscoveryProc()
        _discoverer.add_discovery_processor(_disco_process)
        client.start()
        time.sleep(2)
        self.assertGreater(_disco_process.nb_devices, 0)
        client.disconnect()

    def test_discoverer03(self):
        log_it("Testing Zigbee Discoverer : create codec and get availability")
        client1 = MQTTClient('', self.TARGET)
        client2 = MQTTClient('', self.TARGET)
        _discoverer = ZigbeeDiscoverer(client1)
        _discoverer.add_discovery_processor(ExtendedDiscoveryProc(mqtt_client=client2))

        client1.start()

        time.sleep(2)
        client1.disconnect()
        client2.disconnect()

class TestDiscoTasmota(unittest.TestCase):
    TARGET = 'groseille.back.internal'
    def test_discoverer01(self):
        log_it("Testing Tasmota Discoverer")
        client = MQTTClient('', self.TARGET)
        _discoverer = TasmotaDiscoverer(client)
        client.start()
        time.sleep(2)
        self.assertGreater(len(_discoverer.get_devices()), 0)
        client.disconnect()

    def test_discoverer02(self):
        log_it("Testing Tasmota Tasmota with processor")
        client = MQTTClient('', self.TARGET)
        _discoverer = TasmotaDiscoverer(client)
        _disco_process = BasicDiscoveryProc()
        _discoverer.add_discovery_processor(_disco_process)
        client.start()
        time.sleep(2)
        self.assertGreater(_disco_process.nb_devices, 0)
        client.disconnect()

    def X_test_discoverer03(self):
        log_it("Testing Tasmota Discoverer : create codec and get availability")
        client1 = MQTTClient('', self.TARGET)
        client2 = MQTTClient('', self.TARGET)
        _discoverer = TasmotaDiscoverer(client1)
        _discoverer.add_discovery_processor(ExtendedDiscoveryProc(mqtt_client=client2))

        client1.start()

        time.sleep(2)
        client1.disconnect()
        client2.disconnect()


class TestUnifiedDisco(unittest.TestCase):
    TARGET = 'groseille.back.internal'
    def test_discoverer01(self):
        log_it("Testing Unified Discoverer")
        client = MQTTClient('', self.TARGET)
        _discoverer = UnifiedDiscoverer(client)
        client.start()
        time.sleep(2)
        self.assertGreater(len(_discoverer.get_devices()), 0)
        client.disconnect()

    def test_discoverer02(self):
        log_it("Testing Unified Discoverer with processor")
        client = MQTTClient('', self.TARGET)
        _discoverer = UnifiedDiscoverer(client)
        _disco_process = BasicDiscoveryProc()
        _discoverer.add_discovery_processor(_disco_process)
        client.start()
        time.sleep(2)
        self.assertGreater(_disco_process.nb_devices, 0)
        client.disconnect()

    def test_discoverer03(self):
        log_it("Testing Unified Discoverer : create codec and get availability")
        client1 = MQTTClient('', self.TARGET)
        client2 = MQTTClient('', self.TARGET)
        _discoverer = UnifiedDiscoverer(client1)
        _discoverer.add_discovery_processor(ExtendedDiscoveryProc(mqtt_client=client2))

        client1.start()

        time.sleep(2)
        client1.disconnect()
        client2.disconnect()
