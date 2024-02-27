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
        self.topic_root = f'{topic_base}/{device_name}'
        self.state = False
        self.message_count = 0

        self.client.connect_handler_add(self.on_connect_cb)
        self.client.message_callback_add(self.topic_root + '/set', self.on_message_set)
        self.client.message_callback_add(self.topic_root + '/get', self.on_message_get)

    def _state_to_json(self):
        _state = "ON" if self.state else "OFF"
        _json = json.dumps({"state":_state})
        return _json

    def _process_message_count(self, topic, payload):
        self.message_count += 1
        logger.debug("Mock received on topic : '%s' - payload : %s - message count : %s" ,
                      topic, payload, self.message_count)

    def on_message_set(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        self._process_message_count(message.topic, payload)
        if payload == self.MESSAGE_ON:
            self.state = True
        elif payload == self.MESSAGE_OFF:
            self.state = False
        else:
            logger.error('Receive bad message : %s', payload)
        self.client.publish(self.topic_root, self._state_to_json())


    def on_message_get(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        self._process_message_count(message.topic, payload)
        _state = "ON" if self.state else "OFF"
        message = {"state":_state, "message_count":self.message_count} 
        self.client.publish(self.topic_root, json.dumps(message))

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root + '/+', qos=1)
