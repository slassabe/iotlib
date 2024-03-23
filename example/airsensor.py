#!/usr/local/bin/python3
# coding=utf-8

import time
import logging

from context import Loader


with Loader():

    from iotlib.bridge import DecodingException, MQTTBridge
    from iotlib.processor import AvailabilityPublisher, AvailabilityLogger
    from iotlib.client import MQTTClient
    from iotlib.factory import CodecFactory, Model, Protocol
    from iotlib.virtualdev import (Alarm, Button, HumiditySensor, Motion, Switch,
                                   TemperatureSensor)


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


def test_availability_logger():
    DEVICE_NAME = 'TEMP_SALON'
    BROCKER_NAME = 'groseille.back.internal'
    logging.basicConfig(level=logging.INFO)

    # Create an MQTT client
    client = MQTTClient('', BROCKER_NAME)
    # Create a codec for the device model and protocol
    codec = CodecFactory().create_instance(model=Model.ZB_AIRSENSOR,
                                           protocol=Protocol.Z2M,
                                           device_name=DEVICE_NAME)
    bridge = MQTTBridge(client, codec)
    # Create an availability logger, which logs the availability of the device
    logger = AvailabilityLogger(debug=True)
    # Add the availability logger to the bridge
    bridge.add_availability_processor(logger)
    # Start the MQTT client, which will connect to the broker and start
    # listening for messages
    client.start()
    # Start an infinite loop to handle messages
    loop_infinite()
    # Should display ;
    #  - if the device is configured and available : [INFO] [TEMP_SALON] is available
    #  - if the device is configured and unavailable : [INFO] [TEMP_SALON] is unavailable
    #  Nothing is displayed if the device is not not configured in Zigbee2MQTT


if __name__ == "__main__":
    test_availability_logger()
