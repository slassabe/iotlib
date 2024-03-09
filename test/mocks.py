import json

from iotlib.client import MQTTClient
from iotlib.virtualdev import Switch
from iotlib.virtualdev import (HumiditySensor, TemperatureSensor)
from iotlib.bridge import AbstractCodec, Surrogate, DecodingException

from .helper import log_it, logger, get_broker_name


class MockCodec(AbstractCodec):
    def __init__(self,
                 device_name: str,
                 topic_base: str):
        super().__init__(device_name, topic_base)
        self.property_topic = f'{topic_base}/{device_name}'
        self.state_topic = f'{topic_base}/{device_name}/availability'

        self.v_temp = TemperatureSensor()
        self.v_humi = HumiditySensor()
        self._set_message_handler(self.property_topic,
                                  self.__class__._decode_temp_pl,
                                  self.v_temp)
        self._set_message_handler(self.property_topic,
                                  self.__class__._decode_humi_pl,
                                  self.v_humi)

    def get_availability_topic(self) -> str:
        return self.state_topic

    def decode_avail_pl(self, payload: str) -> bool:
        if payload != 'online' and payload != 'offline' and payload is not None:
            raise DecodingException(f'Payload value error: {payload}')
        else:
            return payload == 'online'

    def _decode_temp_pl(self, topic, payload: dict) -> float:
        _value = json.loads(payload).get(('temperature'))
        if _value is None:
            raise DecodingException(
                f'No "temperature" key in payload : {payload}')
        else:
            return float(_value)

    def _decode_humi_pl(self, topic, payload: dict) -> int:
        _value = json.loads(payload).get('humidity')
        if _value is None:
            raise DecodingException(
                f'No "humidity" key in payload : {payload}')
        else:
            return int(_value)


class MockBridge:

    def __init__(self,
                 mqtt_client: MQTTClient,
                 device_name: str,
                 topic_base: str = None):
        self.codec = MockCodec(device_name, topic_base)
        self.surrogate = Surrogate(mqtt_client, self.codec)



class MockZigbeeSensor:
    def __init__(self,
                 client: MQTTClient,
                 device_name: str,
                 topic_base) -> None:
        self.client = client
        self.device_name = device_name
        self.topic_base = topic_base
        self.topic_root = f'{topic_base}/{device_name}'
        self.state = False
        self.client.connect_handler_add(self.on_connect_cb)

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root, qos=1)

    def publish(self, temperature: float, humidity: int):
        _properties = {"battery": 67.5,
                       "humidity": humidity,
                       "linkquality": 60,
                       "temperature": temperature,
                       "voltage": 2900}
        _message = json.dumps(_properties)
        self.client.publish(self.topic_root, _message)


class MockZigbeeSwitch:
    MESSAGE_ON = '{"state": "ON"}'
    MESSAGE_OFF = '{"state": "OFF"}'

    def __init__(self,
                 client: MQTTClient,
                 device_name: str,
                 v_switch: Switch,
                 topic_base) -> None:
        self.client = client
        self.device_name = device_name
        v_switch.concrete_device = self
        self._v_switch = v_switch

        self.topic_base = topic_base
        self.topic_root = f'{topic_base}/{device_name}'
        self.state = False
        self.message_count = 0

        self.client.connect_handler_add(self.on_connect_cb)
        self.client.message_callback_add(
            self.topic_root + '/set', self.on_message_set)
        self.client.message_callback_add(
            self.topic_root + '/get', self.on_message_get)

    def _state_to_json(self):
        _state = "ON" if self.state else "OFF"
        _json = json.dumps({"state": _state})
        return _json

    def _process_message_count(self, topic, payload):
        self.message_count += 1
        logger.debug("Mock received on topic : '%s' - payload : %s - message count : %s",
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
        message = {"state": _state, "message_count": self.message_count}
        self.client.publish(self.topic_root, json.dumps(message))

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root + '/+', qos=1)
