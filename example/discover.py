#!/usr/local/bin/python3
# coding=utf-8

import time
import logging
import json
from context import Loader


with Loader():

    from iotlib.bridge import DecodingException, MQTTBridge
    from iotlib.processor import AvailabilityPublisher, AvailabilityLogger
    from iotlib.client import MQTTClient
    from iotlib.factory import CodecFactory, Model, Protocol
    from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                                   TemperatureSensor)
    from test.helper import get_broker_name



def loop_infinite() -> None:
    '''Infinite loop to handle messages
    '''
    while True:
        try:
            time.sleep(2)
            print('.', end='')
        except DecodingException as e:
            print(e)
        except KeyboardInterrupt:
            break

def parse_devices(payload: json):
    devices = []
    for entry in payload:
        ieee_address = entry.get("ieee_address")
        friendly_name = entry.get("friendly_name")
        type = entry.get("type")
        definition = entry.get("definition")
        if definition:
            model = definition.get("model")
            vendor = definition.get("vendor")
        else:
            model = None
            vendor = None
        print(f"Type: {type}, Device: {friendly_name}, Model: {model}, Vendor: {vendor}")

    return devices

def get_devices(mqtt_client: MQTTClient):
    devices = []
    def on_message_cb(client, userdata, message):
        payload = str(message.payload.decode("utf-8"))
        #print(f"Topic: {message.topic}, Payload: {payload}")
        dev = parse_devices(json.loads(payload))
        devices.append(dev)
    def on_connect_cb(client, userdata, flags, rc, properties) -> None:
        print("Connected")
        client.subscribe('zigbee2mqtt/bridge/devices')
    mqtt_client.message_callback_add('zigbee2mqtt/bridge/devices',
                                     on_message_cb)
    mqtt_client.connect_handler_add(on_connect_cb)
    mqtt_client.start()

    time.sleep(2)
    return devices

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    client = MQTTClient('', 'groseille.back.internal')
    devives = get_devices(client)