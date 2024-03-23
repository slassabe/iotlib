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
            time.sleep(10)
            print('.', end='')
        except DecodingException as e:
            print(e)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    DEVICE_NAME = 'TEMP_SALON'
    BROCKER_NAME = 'groseille.back.internal'
    logging.basicConfig(level=logging.DEBUG)

    # Create a client
    client = MQTTClient('', BROCKER_NAME)
    #codec = SonoffSnzb02(DEVICE_NAME)
    codec = CodecFactory().create_instance(model=Model.ZB_AIRSENSOR,
                                            protocol=Protocol.Z2M,
                                            device_name=DEVICE_NAME)
    bridge = MQTTBridge(client, codec)
    
    logger = AvailabilityLogger(debug=True)
    bridge.add_availability_processor(logger)
    client.start()

    loop_infinite()
    # Should display ;
    #  - if the device is configured and available : [INFO] [TEMP_SALON] is available
    #  - if the device is configured and unavailable : [INFO] [TEMP_SALON] is unavailable
    #  Nothing is displayed if the device is not not configured in Zigbee2MQTT
