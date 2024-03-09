#!/usr/local/bin/python3
# coding=utf-8

"""Client test

$ source .venv/bin/activate
$ python -m unittest test.test_client
"""
import unittest
import time
import paho.mqtt.client as mqtt
from iotlib.client import MQTTClient

from .helper import log_it, logger, get_broker_name

TOPIC_BASE = 'TEST_A2IOT/client'


class PubSub:
    MESSAGE1 = "message1"
    MESSAGE2 = "message2"
    TOPIC_LEAF = TOPIC_BASE + "/device_name/#"
    TOPIC_ROOT = TOPIC_BASE + "/+/the-topic"
    TOPIC_1 = TOPIC_BASE + "/device_name/the-topic"
    TOPIC_2 = TOPIC_BASE + "/device_name/another-topic"
    TOPIC_3 = TOPIC_BASE + "/another_name/the-topic"

    def __init__(self, client: MQTTClient, to_subscribe=None, to_publish=None):
        self.client = client
        self.to_subscribe = to_subscribe or []
        self.to_publish = to_publish or []
        self.received_on_root = None
        self.received_on_this = None
        self.status_on_root = None

    def on_root_topic_cb(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("Callback DEFAULT : receives message on topic '%s': %s",
                     message.topic, payload)
        self.received_on_root = payload

    def on_this_topic_cb(self, client, userdata, message):
        payload = message.payload.decode("utf-8")
        logger.debug("Callback SPECIFIC : receives message on topic '%s': %s",
                     message.topic, payload)
        self.received_on_this = payload

    def on_connect_cb(self, client, userdata, flags, rc, properties: mqtt.Properties | None) -> None:
        logger.debug(
            'Callback : connected - properties : "%s"', properties)
        for _topic in self.to_subscribe:
            self.client.subscribe(_topic, qos=1)
        self.status_on_root = "connected"

    def on_disconnect_cb(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        logger.debug('Callback : client disconnected - rc : %s', reason_code)
        self.status_on_root = "disconnected"

    def on_subscribe_cb(self, client, userdata, mid, reason_code_list, properties) -> None:
        logger.debug('Callback : subscribe request')
        for _topic, _message in self.to_publish:
            self.client.publish(_topic, _message)


class TestMQTTClient(unittest.TestCase):
    target = get_broker_name()

    def test_connect(self):
        log_it("Testing connection to a broker")
        client = MQTTClient('', self.target)
        client.start()
        time.sleep(2)
        self.assertTrue(client.connected)
        time.sleep(2)
        client.stop()
        self.assertFalse(client.connected)

    def test_pub_sub_00(self):
        log_it("Testing subscribe with default callback")
        test = PubSub(MQTTClient('PubSubClient',
                                     self.target),
                      to_subscribe=[TOPIC_BASE + "/device_name/the-topic"],
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1")],
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)
        test.client.subscribe_handler_add(test.on_subscribe_cb)
        test.client.disconnect_handler_add(test.on_disconnect_cb)
        test.client.start()

        time.sleep(2)
        self.assertTrue(test.status_on_root == "connected")
        self.assertTrue(test.received_on_root == "message1")
        test.client.stop()

    def test_pub_sub_01(self):
        log_it("Testing subscribe with default callback and wildchar subscription")
        test = PubSub(MQTTClient('PubSubClient',
                                     self.target),
                      # <- Why is this required ??
                      to_subscribe=[TOPIC_BASE + "/device_name/the-topic"],
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1")],
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)
        test.client.subscribe_handler_add(test.on_subscribe_cb)
        test.client.disconnect_handler_add(test.on_disconnect_cb)
        test.client.start()

        time.sleep(2)
        self.assertTrue(test.status_on_root == "connected")
        self.assertTrue(test.received_on_root == "message1")
        test.client.stop()

    def test_pub_sub_02(self):
        log_it("Testing subscribe without wildchar callback")

        mqtt_client = MQTTClient('PubSubClient', self.target)
        mqtt_client.client.enable_logger()

        test = PubSub(mqtt_client,
                      to_subscribe=[TOPIC_BASE + "/device_name/the-topic"], 
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1")],
                      )

        test.client.message_callback_add(TOPIC_BASE + "/device_name/the-topic", 
                                         test.on_this_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)
        test.client.subscribe_handler_add(test.on_subscribe_cb)
        test.client.start()

        time.sleep(2)
        self.assertTrue(test.received_on_this == "message1")
        test.client.stop()

    def test_pub_sub_03(self):
        log_it("Mixing both wildchar and regular topic subscription")
        test = PubSub(MQTTClient('PubSubClient', self.target),
                      to_subscribe=[TOPIC_BASE + "/device_name/#"],
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1"),
                                  (TOPIC_BASE + "/device_name/another-topic", "message2")]
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.message_callback_add(TOPIC_BASE + "/device_name/the-topic",
                                         test.on_this_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)     # Required
        test.client.subscribe_handler_add(test.on_subscribe_cb)  # Required
        test.client.start()

        time.sleep(2)

        self.assertTrue(test.received_on_this == "message1")
        self.assertTrue(test.received_on_root == "message2")
        test.client.stop()

    def test_pub_sub_04(self):
        log_it("Testing topic wildcard /root/+/leaf")
        test = PubSub(MQTTClient('PubSubClient',
                                     self.target),
                      to_subscribe=[TOPIC_BASE + "/+/the-topic"],
                      to_publish=[(TOPIC_BASE + "/another_name/the-topic", "message1")]
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)     # Required
        test.client.subscribe_handler_add(test.on_subscribe_cb)  # Required
        test.client.start()

        time.sleep(2)
        self.assertTrue(test.received_on_root == "message1")
        test.client.stop()

    def test_pub_sub_05A(self):
        log_it("Testing topic regular and wildcard concurrency - part 1")
        test = PubSub(MQTTClient('PubSubClient',
                                     self.target),
                      to_subscribe=[TOPIC_BASE + "/+/the-topic"],
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1")]
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.message_callback_add(TOPIC_BASE + "/device_name/the-topic",
                                         test.on_this_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)     # Required
        test.client.subscribe_handler_add(test.on_subscribe_cb)  # Required
        test.client.start()

        time.sleep(2)
        self.assertTrue(test.received_on_this == "message1")
        self.assertIsNone(test.received_on_root)
        test.client.stop()

    def test_pub_sub_05B(self):
        log_it("Testing topic regular and wildcard concurrency - part 2")
        test = PubSub(MQTTClient('PubSubClient',
                                     self.target),
                      to_subscribe=[TOPIC_BASE + "/+/the-topic"],
                      to_publish=[(TOPIC_BASE + "/device_name/the-topic", "message1"),
                                  (TOPIC_BASE + "/another_name/the-topic", "message2")]
                      )

        test.client.default_message_callback_add(test.on_root_topic_cb)
        test.client.message_callback_add(TOPIC_BASE + "/device_name/the-topic",
                                         test.on_this_topic_cb)
        test.client.connect_handler_add(test.on_connect_cb)     # Required
        test.client.subscribe_handler_add(test.on_subscribe_cb)  # Required
        test.client.start()

        time.sleep(2)

        self.assertTrue(test.received_on_this == "message1")
        self.assertTrue(test.received_on_root == "message2")
        test.client.stop()

    def test_fail_01(self):
        log_it("Testing double stop : FAIL")

        test1 = PubSub(MQTTClient('IamAlone', self.target))
        test1.client.connect_handler_add(test1.on_connect_cb)
        test1.client.disconnect_handler_add(test1.on_disconnect_cb)
        test1.client.start()

        time.sleep(2)
        self.assertTrue(test1.status_on_root == "connected")
        test1.client.stop()
        self.assertTrue(test1.status_on_root == "disconnected")
        with self.assertRaises(RuntimeError):
            test1.client.stop()

    def test_fail_02(self):
        """If a client connects with a client id that is in use, 
        and also currently connected then the existing connection is closed."""
        log_it("Testing dual run fail : several clients with same client id")

        # 1) launch test1 client and test it
        test1 = PubSub(MQTTClient('IamAlone', self.target))
        test1.client.connect_handler_add(test1.on_connect_cb)
        test1.client.disconnect_handler_add(test1.on_disconnect_cb)
        test1.client.start()

        time.sleep(2)
        self.assertTrue(test1.status_on_root == "connected")

        # 2) launch test2 client and test it
        test2 = PubSub(MQTTClient('IamAlone', self.target))
        test2.client.connect_handler_add(test2.on_connect_cb)
        test2.client.disconnect_handler_add(test2.on_disconnect_cb)
        test2.client.start()

        time.sleep(2)

        # 3) Verify test1 shut down
        self.assertTrue(test1.status_on_root == "disconnected")
        self.assertTrue(test2.status_on_root == "connected")
        test2.client.stop()

    def X_test_properties(self):
        ##
        # Unable to use
        log_it("Testing properties on connect")
        test = PubSub(MQTTClient('PubSubClient', self.target))

        properties = mqtt.Properties(mqtt.PacketTypes.CONNECT)
        properties.UserProperty = ("topic", "AZERTY")
        test.client.start(properties)
        test.client.connect_handler_add(test.on_connect_cb)
        time.sleep(2)
        self.assertTrue(test.client.connected)


if __name__ == "__main__":
    unittest.main()
