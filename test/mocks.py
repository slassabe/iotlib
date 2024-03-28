#!/usr/local/bin/python3
# coding=utf-8
# pylint: skip-file

import json
import time

from iotlib.client import MQTTClient
from iotlib.virtualdev import Switch
from iotlib.virtualdev import (HumiditySensor, TemperatureSensor)
from iotlib.bridge import MQTTBridge, DecodingException
from iotlib.codec.core import Codec
from iotlib.factory import Model
from .helper import logger


class MockCodec(Codec):
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

    def change_state_request(self, is_on: bool, device_id: int | None) -> tuple[str, str]:
        raise(RuntimeError('Cannot encode state of Sensor'))

    def get_state_request(self, device_id: int | None) -> tuple[str, str]:
        raise(RuntimeError('Cannot get topic control state of Sensor'))


class MockBridge:

    def __init__(self,
                 mqtt_client: MQTTClient,
                 device_name: str,
                 topic_base: str = None):
        self.codec = MockCodec(device_name, topic_base)
        self.surrogate = MQTTBridge(mqtt_client, self.codec)



class MockZigbeeSensor:
    def __init__(self,
                 client: MQTTClient,
                 device_name: str,
                 topic_base: str,
                 model: str) -> None:
        self.client = client
        self.device_name = device_name
        self.model = model
        self.topic_base = topic_base
        self.topic_root = f'{topic_base}/{device_name}'
        self.state = False
        self.client.connect_handler_add(self.on_connect_cb)

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root, qos=1)

    def publish(self, temperature: float, humidity: int):
        _properties = {"battery": 67.5,
                       "humidity" if self.model == Model.ZB_AIRSENSOR else "soil_moisture": humidity,
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

    def _state_to_json(self, on_time: int = None):
        _state = "ON" if self.state else "OFF"
        _json_dict = {"state": _state}
        
        if on_time is not None:
            _json_dict["on_time"] = on_time
            logger.info("Switch %s will be turned off in %s seconds", self, on_time)

        _json = json.dumps(_json_dict)
        return _json

    def _process_message_count(self, topic, payload):
        self.message_count += 1
        logger.debug("Mock received on topic : '%s' - payload : %s - message count : %s",
                     topic, payload, self.message_count)

    def on_message_set(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        self._process_message_count(message.topic, payload)
        _json_payload = json.loads(payload)
        if 'state' not in _json_payload:
            raise DecodingException(f'No state in message: {payload}')
        _state = _json_payload['state']
        if _state == 'ON':
            self.state = True
        elif _state == 'OFF':
            self.state = False
        else:
            raise DecodingException(f'Bad state in message: {payload}')
        _on_time = _json_payload.get('on_time')
        if _on_time is not None:
            _on_time = int(_on_time)
        #logger.info(">>> [%s] state set to %s", self, self._state_to_json(_on_time))
        self.client.publish(self.topic_root, self._state_to_json(_on_time))
        if _on_time is not None:
            time.sleep(_on_time)
            self.state = False
            self.client.publish(self.topic_root, self._state_to_json())
            logger.info("<<< [%s] state set to %s", self, self._state_to_json())


    def on_message_get(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        self._process_message_count(message.topic, payload)
        _state = "ON" if self.state else "OFF"
        message = {"state": _state, "message_count": self.message_count}
        self.client.publish(self.topic_root, json.dumps(message))

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root + '/+', qos=1)

class MockZigbeeMultiSwitch:
    MESSAGE_SWITCH0_ON = '{"state_right": "ON"}'
    MESSAGE_SWITCH0_OFF = '{"state_right": "OFF"}'
    MESSAGE_SWITCH1_ON = '{"state_left": "ON"}'
    MESSAGE_SWITCH1_OFF = '{"state_left": "OFF"}'

    def __init__(self,
                 client: MQTTClient,
                 device_name: str,
                 v_switch0: Switch,
                 v_switch1: Switch,
                 topic_base) -> None:
        self.client = client
        self.device_name = device_name
        self._v_switch0 = v_switch0
        self._v_switch1 = v_switch1

        self.topic_base = topic_base
        self.topic_root = f'{topic_base}/{device_name}'
        self.state0 = False
        self.state1 = False

        self.client.connect_handler_add(self.on_connect_cb)
        self.client.message_callback_add(
            self.topic_root + '/set', self.on_message_set)
        self.client.message_callback_add(
            self.topic_root + '/get', self.on_message_get)


    def on_message_set(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        if payload == self.MESSAGE_SWITCH0_ON:
            self.state0 = True
        elif payload == self.MESSAGE_SWITCH0_OFF:
            self.state0 = False
        elif payload == self.MESSAGE_SWITCH1_ON:
            self.state1 = True
        elif payload == self.MESSAGE_SWITCH1_OFF:
            self.state1 = False
        else:
            logger.error('Receive bad message : %s', payload)
        self.client.publish(self.topic_root, json.dumps(payload))

    def on_message_get(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        _json_pl = json.loads(payload)
        _the_switch = next(iter(_json_pl))
        if _the_switch == 'state_right':
            _the_state = "ON" if self.state0 else "OFF"
        elif _the_switch == 'state_left':
            _the_state = "ON" if self.state1 else "OFF"
        else:
            raise ValueError(f'Bad message: {payload}')
        message = {_the_switch: _the_state}
        self.client.publish(self.topic_root, json.dumps(message))

    def on_connect_cb(self, client, userdata, flags, rc, properties) -> None:
        self.client.subscribe(self.topic_root + '/+', qos=1)
