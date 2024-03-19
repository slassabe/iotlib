#!/usr/local/bin/python3
# coding=utf-8

import time
import logging

from context import Loader


with Loader():

    from iotlib.bridge import DecodingException, MQTTBridge
    from iotlib.processor import AvailabilityPublisher, AvailabilityLogger
    from iotlib.client import MQTTClient
    from iotlib.codec.z2m import DeviceOnZigbee2MQTT, SonoffSnzb02, SonoffSnzb01, SonoffSnzb3, NeoNasAB02B2, SonoffZbminiL
    from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                                   TemperatureSensor)


def enroll_device(client: MQTTClient, codec: DeviceOnZigbee2MQTT, device: str) -> None:
    '''Enroll a device in the system

    Args:
        client (MQTTClient): The client to use for the enrollment.
        codec (DeviceOnZigbee2MQTT): The codec to use for the enrollment.
        device (str): The device to enroll.
    '''
    client.subscribe(codec.get_state_topic(device))
    client.subscribe(codec.get_availability_topic())


def loop_infinite() -> None:
    '''Infinite loop to handle messages
    '''
    while True:
        try:
            time.sleep(10)
            print('.', end='')
        except DecodingException as e:
            print(e)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    DEVICE_NAME = 'TEMP_SALON'
    BROCKER_NAME = 'groseille.back.internal'
    logging.basicConfig(level=logging.INFO)

    # Create a client
    client = MQTTClient('', BROCKER_NAME)
    codec = SonoffSnzb02(DEVICE_NAME)
    bridge = MQTTBridge(client, codec)
    
    logger = AvailabilityLogger(device_name=DEVICE_NAME, debug=True)
    bridge.add_availability_processor(logger)
    client.start()

    loop_infinite()
    # Should display ;
    #  - if the device is configured and available : [INFO] [TEMP_SALON] is available
    #  - if the device is configured and unavailable : [INFO] [TEMP_SALON] is unavailable
    #  Nothing is displayed if the device is not not configured
