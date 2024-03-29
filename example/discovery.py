#!/usr/local/bin/python3
# coding=utf-8

import time
import logging

from context import Loader


with Loader():

    from iotlib.client import MQTTClient
    from iotlib.discoverer import UnifiedDiscoverer
    from iotlib.abstracts import DiscoveryProcessor

def basic_discovery(mqtt_client: MQTTClient):
    _discoverer = UnifiedDiscoverer(mqtt_client)
    time.sleep(2)
    devices = _discoverer.get_devices()
    print(f"Basic discovery - length : {len(devices)}")
    for device in devices:
        print(f" - device: {repr(device)}")

class BasicDiscoveryProc(DiscoveryProcessor):
    def process_discovery_update(self, devices):
        print(f"Discovered {len(devices) :} devices")
        for device in devices:
            print(f" * device: {repr(device)}")

def discover_it(mqtt_client: MQTTClient):
    _discoverer = UnifiedDiscoverer(mqtt_client)
    _discoverer.add_discovery_processor(BasicDiscoveryProc())

if __name__ == "__main__":
    BROKER = 'groseille.back.internal'
    # Create MQTT client
    client = MQTTClient('', BROKER)
    client.start()

    #basic_discovery(client)
    discover_it(client)
    time.sleep(2)
