import json

from iotlib.client import MQTTClientBase
from .utils import log_it, logger, get_broker_name


class MockSwitch:
    MESSAGE_ON = '{"state": "ON"}'
    MESSAGE_OFF = '{"state": "OFF"}'
    
    def __init__(self,
                 client: MQTTClientBase,
                 device_name: str,
                 topic_base) -> None:
        self.client = client
        self.device_name = device_name
        self.topic_base = topic_base
        self.topic_root = f'{self.topic_base}/{self.device_name}'
        self.state = False

        self.client.connect_handler_add(self.on_connect_cb)
        self.client.message_callback_add(self.topic_root + '/set', self.on_message_set)
        self.client.message_callback_add(self.topic_root + '/get', self.on_message_get)

    def on_message_set(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("on_message_set : receives message on topic '%s': %s",
                      message.topic, payload)
        if payload == self.MESSAGE_ON:
            self.state = True
            message = {"state":"ON"}
        elif payload == self.MESSAGE_OFF:
            self.state = False
            message = {"state":"OFF"}
        else:
            logger.error('Receive bad message : %s', payload)
        self.client.publish(self.topic_root, json.dumps(message))


    def on_message_get(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("on_message_get : receives message on topic '%s': %s",
                      message.topic, payload)
        message = {"state":"ON"} if self.state else {"state":"OFF"}
        self.client.publish(self.topic_root, json.dumps(message))

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root + '/#', qos=1)

